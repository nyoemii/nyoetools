from collections import defaultdict
from typing import Any, List, Optional
from nextcord import ButtonStyle, Embed, \
    IntegrationType, Interaction, InteractionContextType, slash_command
from nextcord.ext.commands import Bot, Cog
from nextcord.ui import Button, View, Item

class PollButton(Button[View]):
    def __init__(self, poll_id: str, option_idx: int, label: str):
        super().__init__(
            label=f"{label} (0)",
            custom_id=f"poll_{poll_id}_{option_idx}",
            style=ButtonStyle.blurple
        )
        self.poll_id = poll_id
        self.option_idx = option_idx
        self.original_label = label
        self.poll_votes: defaultdict[str, Any] = defaultdict(dict)

    async def callback(self, interaction: Interaction[Bot]):
        if not interaction.user or not self.view:
            return
        self.poll_votes[self.poll_id][interaction.user.id] = self.option_idx
        
        vote_counts = [0] * 4
        for vote in self.poll_votes[self.poll_id].values():
            vote_counts[vote] += 1

        new_view = View(timeout=None)
        for idx in range(len(vote_counts)):
            if idx >= len(self.view.children):
                continue

            new_button = PollButton(
                poll_id=self.poll_id,
                option_idx=idx,
                label=self.view.children[idx].original_label
            )
            new_button.label = f"{new_button.original_label} ({vote_counts[idx]})"
            if vote_counts[idx] == max(vote_counts):
                new_button.style = ButtonStyle.green
            new_view.add_item(new_button)

        total_votes = sum(vote_counts)
        embed = interaction.message.embeds[0]
        embed.description = f"**Total Votes**: {total_votes}\n\n" + "\n".join(
            f"{self.view.children[i].original_label}: {vote_counts[i]} vote{'s' if vote_counts[i] != 1 else ''}"
            for i in range(len(self.view.children))
        )

        await interaction.response.edit_message(embed=embed, view=new_view)

class Poll(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
    
    @slash_command(
        description="Makes a Poll",
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
    async def poll(interaction: Interaction[Bot], question: str, option1: str, option2: str, option3: str = None, option4: str = None):
        options = [opt for opt in [option1, option2, option3, option4] if opt is not None]
        poll_id = str(interaction.id)

        view = View(timeout=None)
        for idx, option in enumerate(options):
            view.add_item(PollButton(
                poll_id=poll_id,
                option_idx=idx,
                label=option
            ))

        embed = Embed(
            title=f"Poll: {question}",
            description="\n".join(f"• {opt}" for opt in options),
            color=0x5865F2
        )
        embed.set_footer(text="Enter your vote by using the buttons below!")

        await interaction.response.send_message(embed=embed, view=view)