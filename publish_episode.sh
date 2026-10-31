#!/usr/bin/env bash
# Usage: publish_episode.sh <mp3> <title> <description> <morning|evening> [YYYY-MM-DD]
# Audio convention: edge-tts male zh-CN-YunyangNeural + female zh-CN-XiaoxiaoNeural at rate +10%
#   (build/make_audio.py <script.txt> <out.mp3> [+10%] builds it from a 男：/女： script).
# Needs env GH_PODCAST_TOKEN (fine-grained, Contents RW on seanexk/sean-podcast).
set -euo pipefail
MP3="$1"; TITLE="$2"; DESC="$3"; SLOT="$4"; DATE="${5:-$(TZ=Asia/Shanghai date +%F)}"
[[ "$SLOT" == morning || "$SLOT" == evening ]] || { echo "slot must be morning|evening" >&2; exit 1; }
[ -f "$MP3" ] || { echo "no such mp3: $MP3" >&2; exit 1; }
[ -n "${GH_PODCAST_TOKEN:-}" ] || { echo "GH_PODCAST_TOKEN not set" >&2; exit 1; }
DIR="$(cd "$(dirname "$0")" && pwd)"; cd "$DIR"
BASE="https://seanexk.github.io/sean-podcast"; REPO="seanexk/sean-podcast"
NAME="$DATE-$SLOT.mp3"; HOUR=$([ "$SLOT" = morning ] && echo 08 || echo 18)
cp "$MP3" "episodes/$NAME"
python3 - "$NAME" "$TITLE" "$DESC" "$DATE" "$HOUR" "$SLOT" <<'PY'
import json,sys,datetime
name,title,desc,date,hour,slot=sys.argv[1:]
d=datetime.datetime.strptime(f"{date} {hour}","%Y-%m-%d %H")
pub=d.strftime("%a, %d %b %Y %H:00:00 +0800")
eps=[e for e in json.load(open("episodes.json")) if e["file"]!=name]
eps.append({"file":name,"title":title,"description":desc,"pubDate":pub,"guid":f"sean-news-{date}-{slot}"})
eps.sort(key=lambda e:e["file"])
json.dump(eps,open("episodes.json","w"),ensure_ascii=False,indent=1)
PY
python3 gen_feed.py "$BASE"
python3 -c "import xml.dom.minidom as m;m.parse('feed.xml')"
AUTH="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GH_PODCAST_TOKEN" | base64 -w0)"
git add -A
git -c user.name="News Bot" -c user.email="seanexk@users.noreply.github.com" commit -qm "Episode $DATE $SLOT" || true
git -c http.extraHeader="$AUTH" push -q "https://github.com/$REPO.git" HEAD:main
# wait for Pages to serve the new mp3
for i in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -I "$BASE/episodes/$NAME")
  [ "$code" = 200 ] && grep -q "$NAME" <(curl -s "$BASE/feed.xml?t=$(date +%s)") && { echo "published $BASE/episodes/$NAME"; exit 0; }
  sleep 15
done
echo "pushed, but Pages not serving yet after 10 min" >&2; exit 2
