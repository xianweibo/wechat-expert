import json, sys, datetime
d = json.load(sys.stdin)
v = d["data"]
print("Title:", v["title"][:40])
r = v.get("rights", {})
print("is_charging_arc:", r.get("is_charging_arc"))
print("ugc_pay:", r.get("ugc_pay"))
print("aid:", v.get("aid"))
pd = v.get("pubdate", 0)
print("pubdate:", datetime.datetime.fromtimestamp(pd).strftime("%Y-%m-%d") if pd else "N/A")