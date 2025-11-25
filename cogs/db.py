import nextcord
from nextcord.ext import commands
from nextcord import Interaction, SlashOption, IntegrationType, InteractionContextType
import requests
from datetime import datetime
from typing import List, Dict, Optional
from requests import HTTPError

url = "https://v6.db.transport.rest"


class ConnectionView(nextcord.ui.View):
    """View with navigation buttons for train connections."""

    def __init__(self, embeds: List[nextcord.Embed], user_id: int):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.embeds = embeds
        self.current_page = 0
        self.user_id = user_id
        self.update_buttons()

    def update_buttons(self):
        """Update button states based on current page."""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1
        self.previous_button.label = "← Previous"
        self.next_button.label = "Next →"

    @nextcord.ui.button(
        label="← Previous", style=nextcord.ButtonStyle.primary, disabled=True
    )
    async def previous_button(
        self, button: nextcord.ui.Button, interaction: Interaction
    ):
        """Go to previous connection."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This is not your search!", ephemeral=True
            )
            return

        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(
                embed=self.embeds[self.current_page], view=self
            )

    @nextcord.ui.button(label="Next →", style=nextcord.ButtonStyle.primary)
    async def next_button(self, button: nextcord.ui.Button, interaction: Interaction):
        """Go to next connection."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This is not your search!", ephemeral=True
            )
            return

        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(
                embed=self.embeds[self.current_page], view=self
            )

    @nextcord.ui.button(label="🗑️", style=nextcord.ButtonStyle.danger)
    async def delete_button(self, button: nextcord.ui.Button, interaction: Interaction):
        """Delete the message."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This is not your search!", ephemeral=True
            )
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
                f"{url}/locations", params={"query": query, "results": limit}
            )
            response.raise_for_status()
            stations = response.json()
            return [s for s in stations if s.get("type") in ["station", "stop"]]
        except requests.RequestException as e:
            print(f"Error searching stations: {e}")
            return []

    def get_connections(
        self, from_id: str, to_id: str, departure: str, results: int = 5
    ) -> List[Dict]:
        """Get train connections between two stations."""
        try:
            response = requests.get(
                f"{url}/journeys",
                params={
                    "from": from_id,
                    "to": to_id,
                    "departure": departure,
                    "results": results,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("journeys", [])
        except requests.RequestException as e:
            print(f"Error fetching connections: {e}")
            return []

    def format_duration(self, minutes: int) -> str:
        """Format duration in minutes to hours and minutes."""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"

    def create_connection_embed(
        self, journey: Dict, idx: int, total: int, from_name: str, to_name: str
    ) -> nextcord.Embed:
        """Create an embed for a single connection."""
        first_leg = journey["legs"][0]
        last_leg = journey["legs"][-1]

        dep_time = datetime.fromisoformat(first_leg["departure"].replace("Z", "+00:00"))
        arr_time = datetime.fromisoformat(last_leg["arrival"].replace("Z", "+00:00"))

        duration_mins = int((arr_time - dep_time).total_seconds() / 60)
        transfers = len(journey["legs"]) - 1

        embed = nextcord.Embed(
            title=f"🚄 Connection {idx} of {total}",
            description=f"**{from_name}** → **{to_name}**",
            color=0x667EEA,
            timestamp=dep_time,
        )

        embed.add_field(
            name="⏰ Departure", value=dep_time.strftime("%H:%M"), inline=True
        )

        embed.add_field(
            name="🏁 Arrival", value=arr_time.strftime("%H:%M"), inline=True
        )

        embed.add_field(
            name="⏱️ Duration", value=self.format_duration(duration_mins), inline=True
        )

        embed.add_field(name="🔄 Transfers", value=str(transfers), inline=True)

        route_lines = []
        for leg in journey["legs"]:
            line_name = leg.get("line", {}).get("name", "🚶 Walk")
            origin = leg["origin"]["name"]
            dest = leg["destination"]["name"]

            dep = datetime.fromisoformat(leg["departure"].replace("Z", "+00:00"))
            arr = datetime.fromisoformat(leg["arrival"].replace("Z", "+00:00"))

            route_lines.append(
                f"**{line_name}**\n"
                f"{origin} ({dep.strftime('%H:%M')}) → {dest} ({arr.strftime('%H:%M')})"
            )

        embed.add_field(name="🚆 Route", value="\n\n".join(route_lines), inline=False)

        embed.set_footer(text="Deutsche Bahn API • Use the buttons below to navigate")

        return embed

    @nextcord.slash_command(
        name="train",
        description="Search for train connections in Germany",
        integration_types=[
            IntegrationType.user_install,
            IntegrationType.guild_install,
        ],
        contexts=[
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel,
        ],
    )
    async def train(
        self,
        interaction: Interaction,
        from_station: str = SlashOption(
            name="from",
            description="Departure station (e.g., München Hbf)",
            required=True,
        ),
        to_station: str = SlashOption(
            name="to",
            description="Destination station (e.g., Berlin Hbf)",
            required=True,
        ),
        date: Optional[str] = SlashOption(
            name="date",
            description="Date (YYYY-MM-DD, default: today)",
            required=False,
            default=None,
        ),
        time: Optional[str] = SlashOption(
            name="time",
            description="Time (HH:MM, default: now)",
            required=False,
            default=None,
        ),
    ):
        """Search for train connections between two stations."""
        await interaction.response.defer()

        try:
            from_stations = self.search_stations(from_station)
            to_stations = self.search_stations(to_station)

            if not from_stations:
                await interaction.followup.send(
                    f"❌ No station found for: `{from_station}`", ephemeral=True
                )
                return

            if not to_stations:
                await interaction.followup.send(
                    f"❌ No station found for: `{to_station}`", ephemeral=True
                )
                return

            from_station_obj = from_stations[0]
            to_station_obj = to_stations[0]

            try:
                if date and time:
                    departure_time = datetime.strptime(
                        f"{date} {time}", "%Y-%m-%d %H:%M"
                    )
                elif time:
                    today = datetime.now().date()
                    departure_time = datetime.strptime(
                        f"{today} {time}", "%Y-%m-%d %H:%M"
                    )
                else:
                    departure_time = datetime.now()
            except ValueError:
                await interaction.followup.send(
                    "❌ Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time.",
                    ephemeral=True,
                )
                return

            departure_iso = departure_time.isoformat()
            journeys = self.get_connections(
                from_station_obj["id"], to_station_obj["id"], departure_iso
            )

            if not journeys:
                await interaction.followup.send(
                    f"❌ No connections found from **{from_station_obj['name']}** to **{to_station_obj['name']}**"
                )
                return

            embeds = []
            for idx, journey in enumerate(journeys[:5], 1):
                embed = self.create_connection_embed(
                    journey,
                    idx,
                    len(journeys[:5]),
                    from_station_obj["name"],
                    to_station_obj["name"],
                )
                embeds.append(embed)

            view = ConnectionView(embeds, interaction.user.id)

            await interaction.followup.send(embed=embeds[0], view=view)

        except HTTPError as httpe:
            print(httpe)
            await interaction.send(f"An error occured:\n```bash\n{httpe}```")
        except Exception as e:
            print(e)
            await interaction.send(f"An error occured:\n```bash\n{e}```")


def setup(bot):
    bot.add_cog(DeutscheBahn(bot))
