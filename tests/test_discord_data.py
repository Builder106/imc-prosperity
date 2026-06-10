import json

from src.rag.discord_data import load_discord_exports


def test_load_discord_exports_reads_messages(tmp_path):
    discord_dir = tmp_path / "discord"
    discord_dir.mkdir()
    export_path = discord_dir / "round-2-chat.json"
    export_path.write_text(
        json.dumps(
            {
                "guild": {"name": "IMC Prosperity"},
                "channel": {"name": "round-2-chat"},
                "messages": [
                    {
                        "id": "1",
                        "timestamp": "2026-04-17T12:00:00.0000000+00:00",
                        "content": "Kelp spread looks tighter today.",
                        "author": {"name": "alice"},
                        "type": "Default",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    docs = load_discord_exports(discord_dir, chunk_size=500)

    assert len(docs) == 1
    assert "Kelp spread looks tighter today." in docs[0].page_content
    assert docs[0].metadata["type"] == "discord"
    assert docs[0].metadata["channel"] == "round-2-chat"
    assert docs[0].metadata["guild"] == "IMC Prosperity"


def test_load_discord_exports_filters_non_default_and_empty(tmp_path):
    discord_dir = tmp_path / "discord"
    discord_dir.mkdir()
    export_path = discord_dir / "announcements.json"
    export_path.write_text(
        json.dumps(
            {
                "guild": {"name": "IMC Prosperity"},
                "channel": {"name": "announcements"},
                "messages": [
                    {
                        "id": "1",
                        "timestamp": "2026-04-17T12:00:00.0000000+00:00",
                        "content": "",
                        "author": {"name": "system"},
                        "type": "Default",
                    },
                    {
                        "id": "2",
                        "timestamp": "2026-04-17T12:01:00.0000000+00:00",
                        "content": "Pinned a message",
                        "author": {"name": "system"},
                        "type": "ChannelPinnedMessage",
                    },
                    {
                        "id": "3",
                        "timestamp": "2026-04-17T12:02:00.0000000+00:00",
                        "content": "Round 2 starts tomorrow.",
                        "author": {"name": "mod"},
                        "type": "Default",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    docs = load_discord_exports(discord_dir, chunk_size=500)

    assert len(docs) == 1
    assert "Round 2 starts tomorrow." in docs[0].page_content
    assert "Pinned a message" not in docs[0].page_content


def test_load_discord_exports_chunks_large_threads(tmp_path):
    discord_dir = tmp_path / "discord"
    discord_dir.mkdir()
    export_path = discord_dir / "strategy.json"
    export_path.write_text(
        json.dumps(
            {
                "guild": {"name": "IMC Prosperity"},
                "channel": {"name": "strategy"},
                "messages": [
                    {
                        "id": "1",
                        "timestamp": "2026-04-17T12:00:00.0000000+00:00",
                        "content": "A" * 1400,
                        "author": {"name": "alice"},
                        "type": "Default",
                    },
                    {
                        "id": "2",
                        "timestamp": "2026-04-17T12:01:00.0000000+00:00",
                        "content": "B" * 1400,
                        "author": {"name": "bob"},
                        "type": "Default",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    docs = load_discord_exports(discord_dir, chunk_size=1000)

    assert len(docs) >= 2
    assert all(len(doc.page_content) <= 1200 for doc in docs)
