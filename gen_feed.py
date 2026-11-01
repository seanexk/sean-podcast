import json,os,subprocess,sys
from xml.sax.saxutils import escape as e
base=sys.argv[1].rstrip('/') if len(sys.argv)>1 else "https://EXAMPLE.invalid/podcast"
d=os.path.dirname(os.path.abspath(__file__))
items=[]
for ep in reversed(json.load(open(f"{d}/episodes.json"))):
    p=f"{d}/episodes/{ep['file']}"; size=os.path.getsize(p)
    dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]))
    m,s=divmod(int(round(dur)),60)
    items.append(f"""    <item>
      <title>{e(ep['title'])}</title>
      <description>{e(ep['description'])}</description>
      <enclosure url="{base}/episodes/{ep['file']}" length="{size}" type="audio/mpeg"/>
      <guid isPermaLink="false">{ep['guid']}</guid>
      <pubDate>{ep['pubDate']}</pubDate>
      <itunes:duration>{m:02d}:{s:02d}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <itunes:episodeType>full</itunes:episodeType>
    </item>""")
xml=f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Sean Podcast</title>
    <link>{base}/</link>
    <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>zh-cn</language>
    <description>Sean 的个人播客：每日新闻简报，以及更多内容。Sean's personal podcast: daily news briefings and more.</description>
    <itunes:author>Sean</itunes:author>
    <itunes:summary>Sean 的个人播客：每日新闻简报，以及更多内容。</itunes:summary>
    <itunes:image href="{base}/cover-v3.jpg"/>
    <itunes:category text="News"><itunes:category text="Daily News"/></itunes:category>
    <itunes:category text="Society &amp; Culture"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <itunes:block>Yes</itunes:block>
{chr(10).join(items)}
  </channel>
</rss>
"""
open(f"{d}/feed.xml","w").write(xml)
print("wrote feed.xml for",base)
