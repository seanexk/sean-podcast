import asyncio,sys,subprocess,os,re
import edge_tts
script,out,rate=sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else "+10%"
V={"男":"zh-CN-YunyangNeural","女":"zh-CN-XiaoxiaoNeural"}
lines=[l.strip() for l in open(script,encoding="utf-8") if l.strip()]
segs=[]
for l in lines:
    m=re.match(r"^(男|女)[：:](.*)$",l)
    if m: segs.append((V[m.group(1)],m.group(2).strip()))
async def main():
    d=os.path.join(os.path.dirname(os.path.abspath(out)),"segs"); os.makedirs(d,exist_ok=True)
    files=[]
    for i,(v,t) in enumerate(segs):
        f=f"{d}/{i:03d}.mp3"
        for a in range(3):
            try: await edge_tts.Communicate(t,v,rate=rate).save(f); break
            except Exception as e:
                if a==2: raise
        files.append(f)
    lst=f"{d}/list.txt"; open(lst,"w").write("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",lst,"-ac","1","-ar","24000","-b:a","160k",out],check=True)
asyncio.run(main()); print("segments",len(segs))
