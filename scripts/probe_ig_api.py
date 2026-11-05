# -*- coding: utf-8 -*-
"""在已登录的 IG 页面上下文里探测标签/关键词接口"""
import json
import sys

from DrissionPage import Chromium

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9222
TAG = sys.argv[2] if len(sys.argv) > 2 else "兩餸飯"

JS = r"""
async (tag) => {
  const out = {};
  const appId = '936619743392459';
  const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  const h = {'x-ig-app-id': appId, 'x-csrftoken': csrf, 'content-type':
             'application/x-www-form-urlencoded; charset=UTF-8'};
  async function probe(name, url, opt) {
    try {
      const r = await fetch(url, opt || {headers: h, credentials: 'include'});
      const txt = await r.text();
      let keys = null, sample = txt.slice(0, 200);
      try { const j = JSON.parse(txt); keys = Object.keys(j); } catch (e) {}
      out[name] = {status: r.status, keys: keys, len: txt.length, sample: sample};
    } catch (e) { out[name] = {error: String(e)}; }
  }
  await probe('web_info', '/api/v1/tags/web_info/', {
      method: 'POST', headers: h, credentials: 'include',
      body: 'tag_name=' + encodeURIComponent(tag)});
  await probe('info', '/api/v1/tags/' + encodeURIComponent(tag) + '/info/', {credentials: 'include'});
  await probe('sections', '/api/v1/tags/' + encodeURIComponent(tag) + '/sections/', {
      method: 'POST', headers: h, credentials: 'include', body: ''});
  await probe('topsearch', '/web/search/topsearch/?context=blended&query=' + encodeURIComponent(tag),
      {credentials: 'include'});
  return out;
}
"""


def main():
    br = Chromium(PORT)
    tab = br.latest_tab
    tab.get("https://www.instagram.com/")
    import time
    time.sleep(3)
    res = tab.run_js(JS, TAG)
    print(json.dumps(res, ensure_ascii=False, indent=1)[:3000])


if __name__ == "__main__":
    main()
