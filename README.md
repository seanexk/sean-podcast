# Sean Podcast

Sean's personal podcast: daily news briefings and more. Unlisted (itunes:block), hosted on GitHub Pages.

- Feed: https://seanexk.github.io/sean-podcast/feed.xml
- Add in Apple Podcasts: Library → ⋯ → Follow a Show by URL.

New episode: `GH_PODCAST_TOKEN=... ./publish_episode.sh <mp3> "<title>" "<description>" morning|evening [YYYY-MM-DD]`
(copies the mp3 into `episodes/`, updates `episodes.json`, runs `gen_feed.py`, commits, pushes, waits for Pages).
Audio convention: edge-tts, male zh-CN-YunyangNeural + female zh-CN-XiaoxiaoNeural, rate +10%.
