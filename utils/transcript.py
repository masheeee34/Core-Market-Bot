"""Génération de transcripts HTML depuis l'historique d'un salon de ticket."""

import html
import io

import discord

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Transcript — {channel}</title>
<style>
  body {{ background: #313338; color: #dbdee1; font-family: 'gg sans', 'Segoe UI', sans-serif; margin: 0; padding: 24px; }}
  .header {{ border-bottom: 1px solid #3f4147; padding-bottom: 16px; margin-bottom: 16px; }}
  .header h1 {{ margin: 0 0 4px; font-size: 20px; color: #f2f3f5; }}
  .header p {{ margin: 0; color: #949ba4; font-size: 13px; }}
  .msg {{ display: flex; gap: 12px; padding: 6px 0; }}
  .avatar {{ width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0; }}
  .author {{ font-weight: 600; color: #f2f3f5; margin-right: 8px; }}
  .timestamp {{ color: #949ba4; font-size: 11px; }}
  .content {{ white-space: pre-wrap; word-break: break-word; font-size: 14px; }}
  .attachment {{ color: #00a8fc; font-size: 13px; }}
  .embed {{ border-left: 4px solid #5865f2; background: #2b2d31; padding: 8px 12px; margin-top: 4px; border-radius: 4px; font-size: 13px; }}
</style>
</head>
<body>
<div class="header">
  <h1>#{channel}</h1>
  <p>{count} messages — généré le {generated}</p>
</div>
{messages}
</body>
</html>"""

MSG_TEMPLATE = """<div class="msg">
  <img class="avatar" src="{avatar}" alt="">
  <div>
    <span class="author">{author}</span><span class="timestamp">{timestamp}</span>
    <div class="content">{content}</div>
    {extras}
  </div>
</div>"""


async def generate_transcript(channel: discord.TextChannel) -> discord.File:
    """Parcourt l'historique du salon (du plus ancien au plus récent) et produit un fichier HTML."""
    parts: list[str] = []
    count = 0

    async for message in channel.history(limit=None, oldest_first=True):
        count += 1
        extras = ""
        for attachment in message.attachments:
            extras += f'<div class="attachment">📎 <a href="{html.escape(attachment.url)}">{html.escape(attachment.filename)}</a></div>'
        for embed in message.embeds:
            title = html.escape(embed.title or "")
            desc = html.escape(embed.description or "")
            extras += f'<div class="embed"><b>{title}</b><br>{desc}</div>'

        parts.append(
            MSG_TEMPLATE.format(
                avatar=html.escape(message.author.display_avatar.url),
                author=html.escape(message.author.display_name),
                timestamp=message.created_at.strftime("%d/%m/%Y %H:%M"),
                content=html.escape(message.content or ""),
                extras=extras,
            )
        )

    rendered = HTML_TEMPLATE.format(
        channel=html.escape(channel.name),
        count=count,
        generated=discord.utils.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
        messages="\n".join(parts),
    )

    buffer = io.BytesIO(rendered.encode("utf-8"))
    return discord.File(buffer, filename=f"transcript-{channel.name}.html")
