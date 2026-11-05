# -*- coding: utf-8 -*-
"""探测 tag sections 里能拿到多少条 media、字段长什么样"""
import json
import sys
import time

from DrissionPage import Chromium

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9222
TAG = sys.argv[2] if len(sys.argv) > 2 else "兩餸飯"

JS = r"""
async (tag) => {
  const csrf=(document.cookie.match(/csrftoken=([^;]+)/)||[])[1]||'';
  const h={'x-ig-app-id':'936619743392459','x-csrftoken':csrf,'content-type':'application/x-www-form-urlencoded; charset=UTF-8'};
  const r=await fetch('/api/v1/tags/'+encodeURIComponent(tag)+'/sections/',{method:'POST',headers:h,credentials:'include',body:''});
  const j=await r.json();
  const medias=[];
  const walk=(o)=>{
    if(!o||typeof o!=='object')return;
    if(o.media&&o.media.code){medias.push(o.media); }
    for(const k in o){ if(k!=='media') walk(o[k]); }
  };
  for(const s of (j.sections||[])) walk(s.layout_content);
  const uniq={};
  medias.forEach(m=>uniq[m.pk]=m);
  const arr=Object.values(uniq);
  return {
    more_available:j.more_available, next_max_id:j.next_max_id, next_page:j.next_page,
    section_types:(j.sections||[]).map(s=>s.feed_type+'/'+s.layout_type),
    count:arr.length,
    ts:[Math.min(...arr.map(m=>m.taken_at||0)), Math.max(...arr.map(m=>m.taken_at||0))],
    keys:Object.keys(arr[0]||{}),
    user_keys:Object.keys((arr[0]||{}).user||{}),
    image_versions:((arr[0]||{}).image_versions2||{}).candidates?((arr[0]||{}).image_versions2.candidates.map(c=>c.width+'x'+c.height).slice(0,5)):null,
    sample:arr.slice(0,3).map(m=>({
      code:m.code,pk:m.pk,taken_at:m.taken_at,mt:m.media_type,
      likes:m.like_count,cmts:m.comment_count,
      user:(m.user||{}).username,
      cap:((m.caption||{}).text||'').slice(0,80),
      loc:(m.location||{}).name
    }))
  };
}
"""


def main():
    br = Chromium(PORT)
    tab = br.latest_tab
    tab.get("https://www.instagram.com/")
    time.sleep(3)
    res = tab.run_js(JS, TAG)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
