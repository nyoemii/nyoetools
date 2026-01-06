import discord
from discord import app_commands
from discord.ext import commands
import requests
from datetime import datetime
from typing import List, Dict, Optional
from requests import HTTPError

url = "https://v6.db.transport.rest"

class RemarksModal(discord.ui.Modal, title="Journey Remarks"):
    """Modal to display remarks for a journey."""
    remarks_input = discord.ui.TextInput(
        label="Remarks",
        style=discord.TextStyle.paragraph,
        required=False
    )
    
    def __init__(self, remarks_text: str):
        super().__init__()
        self.remarks_input.default = remarks_text

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

class ConnectionView(discord.ui.View):
    """View with navigation buttons for train connections."""

    def __init__(self, embeds: List[discord.Embed], user_id: int, journeys: List[Dict]):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.embeds = embeds
        self.current_page = 0
        self.user_id = user_id
        self.journeys = journeys
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page."""
        self.previous_btn.disabled = self.current_page == 0
        self.next_btn.disabled = self.current_page == len(self.embeds) - 1
        self.previous_btn.label = f"← Previous"
        self.next_btn.label = f"Next →"
    
    @discord.ui.button(label="← Previous", style=discord.ButtonStyle.primary, disabled=True)
    async def previous_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous connection."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your search!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(label="Next →", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next connection."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your search!", ephemeral=True)
            return
        
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(label="📝 Remarks", style=discord.ButtonStyle.secondary)
    async def remarks_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show remarks for current journey."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your search!", ephemeral=True)
            return

        journey = self.journeys[self.current_page]
        remarks_list = []

        # Collect remarks from all legs
        for i, leg in enumerate(journey.get('legs', []), 1):
            leg_remarks = leg.get('remarks', [])
            if leg_remarks:
                line_name = leg.get('line', {}).get('name', 'Walk')
                origin = leg['origin']['name']
                dest = leg['destination']['name']
                remarks_list.append(f"**Leg {i}: {line_name}** ({origin} → {dest})")

                for remark in leg_remarks:
                    remark_text = remark.get('text', '')
                    remark_summary = remark.get('summary', '')
                    if remark_summary:
                        remarks_list.append(f"• {remark_summary}: {remark_text}")
                    elif remark_text:
                        remarks_list.append(f"• {remark_text}")
                remarks_list.append("")  # Empty line between legs

        # Collect journey-level remarks
        journey_remarks = journey.get('remarks', [])
        if journey_remarks:
            remarks_list.append("**Journey Remarks:**")
            for remark in journey_remarks:
                remark_text = remark.get('text', '')
                remark_summary = remark.get('summary', '')
                if remark_summary:
                    remarks_list.append(f"• {remark_summary}: {remark_text}")
                elif remark_text:
                    remarks_list.append(f"• {remark_text}")

        if remarks_list:
            remarks_text = "\n".join(remarks_list)
            # Truncate if too long for modal (max 4000 chars)
            if len(remarks_text) > 3900:
                remarks_text = remarks_text[:3900] + "\n... (truncated)"
            modal = RemarksModal(remarks_text)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("No remarks available for this journey.", ephemeral=True)

    @discord.ui.button(label="🗑️", style=discord.ButtonStyle.danger)
    async def delete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Delete the message."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your search!", ephemeral=True)
            return

        await interaction.message.delete()
        self.stop()

class DeutscheBahn(commands.Cog):
    """Deutsche Bahn train connection search commands."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def search_stations(self, query: str, limit: int = 25) -> List[Dict]:
        """Search for train stations by name."""
        try:
            response = requests.get(
                f"{url}/locations",
                params={"query": query, "results": limit}
            )
            response.raise_for_status()
            stations = response.json()
            return [s for s in stations if s.get('type') in ['station', 'stop']]
        except requests.RequestException as e:
            print(f"Error searching stations: {e}")
            return []
    
    def get_connections(self, from_id: str, to_id: str, departure: str, results: int = 5) -> List[Dict]:
        """Get train connections between two stations."""
        try:
            response = requests.get(
                f"{url}/journeys",
                params={
                    "from": from_id,
                    "to": to_id,
                    "departure": departure,
                    "results": results
                }
            )
            response.raise_for_status()
            data = response.json()
            return data.get('journeys', [])
        except requests.RequestException as e:
            print(f"Error fetching connections: {e}")
            return []
    
    def format_duration(self, minutes: int) -> str:
        """Format duration in minutes to hours and minutes."""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"
    
    def create_connection_embed(self, journey: Dict, idx: int, total: int, from_name: str, to_name: str, from_id: str, to_id: str) -> discord.Embed:
        """Create an embed for a single connection."""
        first_leg = journey['legs'][0]
        last_leg = journey['legs'][-1]

        dep_time = datetime.fromisoformat(first_leg['departure'].replace('Z', '+00:00'))
        arr_time = datetime.fromisoformat(last_leg['arrival'].replace('Z', '+00:00'))

        duration_mins = int((arr_time - dep_time).total_seconds() / 60)
        transfers = len(journey['legs']) - 1

        embed = discord.Embed(
            title=f"🚄 Connection {idx} of {total}",
            description=f"**{from_name}** ({from_id}) → **{to_name}** ({to_id})",
            color=0x667eea,
            timestamp=dep_time
        )
        
        embed.add_field(
            name="⏰ Departure",
            value=dep_time.strftime('%H:%M'),
            inline=True
        )
        
        embed.add_field(
            name="🏁 Arrival",
            value=arr_time.strftime('%H:%M'),
            inline=True
        )
        
        embed.add_field(
            name="⏱️ Duration",
            value=self.format_duration(duration_mins),
            inline=True
        )
        
        embed.add_field(
            name="🔄 Transfers",
            value=str(transfers),
            inline=True
        )

        # Add price if available
        price_info = journey.get('price')
        if price_info:
            amount = price_info.get('amount')
            currency = price_info.get('currency', 'EUR')
            if amount is not None:
                embed.add_field(
                    name="💰 Price",
                    value=f"{amount:.2f} {currency}",
                    inline=True
                )

        route_lines = []
        for leg in journey['legs']:
            line_name = leg.get('line', {}).get('name', '🚶 Walk')
            origin = leg['origin']['name']
            dest = leg['destination']['name']
            
            dep = datetime.fromisoformat(leg['departure'].replace('Z', '+00:00'))
            arr = datetime.fromisoformat(leg['arrival'].replace('Z', '+00:00'))
            
            route_lines.append(
                f"**{line_name}**\n"
                f"{origin} ({dep.strftime('%H:%M')}) → {dest} ({arr.strftime('%H:%M')})"
            )
        
        embed.add_field(
            name="🚆 Route",
            value="\n\n".join(route_lines),
            inline=False
        )
        
        embed.set_footer(text="Deutsche Bahn API • Use the buttons below to navigate")
        
        return embed
    
    @app_commands.command(
        name="train",
        description="Search for train connections in Germany"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        from_station="Departure station (e.g., München Hbf)",
        to_station="Destination station (e.g., Berlin Hbf)",
        date="Date (YYYY-MM-DD, default: today)",
        time="Time (HH:MM, default: now)"
    )
    async def train(
        self,
        interaction: discord.Interaction,
        from_station: str,
        to_station: str,
        date: Optional[str] = None,
        time: Optional[str] = None
    ):
        """Search for train connections between two stations."""
        await interaction.response.defer()
        
        try:

            from_stations = self.search_stations(from_station)
            to_stations = self.search_stations(to_station)
            
            if not from_stations:
                await interaction.followup.send(
                    f"❌ No station found for: `{from_station}`",
                    ephemeral=True
                )
                return
            
            if not to_stations:
                await interaction.followup.send(
                    f"❌ No station found for: `{to_station}`",
                    ephemeral=True
                )
                return
            
            from_station_obj = from_stations[0]
            to_station_obj = to_stations[0]
            
            try:
                if date and time:
                    departure_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                elif time:
                    today = datetime.now().date()
                    departure_time = datetime.strptime(f"{today} {time}", "%Y-%m-%d %H:%M")
                else:
                    departure_time = datetime.now()
            except ValueError:
                await interaction.followup.send(
                    "❌ Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time.",
                    ephemeral=True
                )
                return
            
            departure_iso = departure_time.isoformat()
            journeys = self.get_connections(
                from_station_obj['id'],
                to_station_obj['id'],
                departure_iso
            )
            
            if not journeys:
                await interaction.followup.send(
                    f"❌ No connections found from **{from_station_obj['name']}** to **{to_station_obj['name']}**"
                )
                return
            
            embeds = []
            journey_list = journeys[:5]
            for idx, journey in enumerate(journey_list, 1):
                embed = self.create_connection_embed(
                    journey,
                    idx,
                    len(journey_list),
                    from_station_obj['name'],
                    to_station_obj['name'],
                    from_station_obj['id'],
                    to_station_obj['id']
                )
                embeds.append(embed)

            view = ConnectionView(embeds, interaction.user.id, journey_list)

            await interaction.followup.send(embed=embeds[0], view=view)

        except HTTPError as httpe:
            print(httpe)
            await interaction.followup.send(f"An error occured:\n```bash\n{httpe}```")
        except Exception as e:
            print(e)
            await interaction.followup.send(f"An error occured:\n```bash\n{e}```")

async def setup(bot):
    """Required setup function for cog loading"""
    await bot.add_cog(DeutscheBahn(bot))
