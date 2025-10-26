from fastapi import FastAPI
app = FastAPI()
@app.get("/health")
def health():
    return {"ok": True}

@app.get("/sg_demand")
def sg_demand(cats: str, days: int = 30):
    # まずはダミー（後でPlaywright実装に差し替え）
    items = [
        {"sg_id":"sg_123","title":"Washi Tape Sakura","brand":"BrandA",
         "attrs":{"material":"paper","width_mm":15},"price_p25":6.2,"price_median":8.5,
         "reviews_30d":74,"demand_index":0.78,"comp_intensity":0.35},
        {"sg_id":"sg_456","title":"Tenugui A","brand":"BrandB","attrs":{"material":"cotton"},
         "price_p25":12.0,"price_median":16.0,"reviews_30d":21,"demand_index":0.52,"comp_intensity":0.20},
    ]
    return {"items": items}

@app.post("/match")
def match(req: MatchReq):
    out = []
    for it in req.sg_items:
        JP["sim"] = JP["jp_title"].apply(lambda t: fuzz.token_set_ratio(it.title, t)/100.0)
        top = JP.sort_values("sim", ascending=False).head(1).iloc[0]
        out.append({
            "sg_id": it.sg_id,
            "jp_id": top.jp_id,
            "jp_price_jpy": float(top.price_jpy),
            "sim_text": float(top.sim),
            "weight_g": float(top.weight_g),
            "thickness_cm": float(top.thickness_cm),
            "jp_url": top.url,
        })
    return {"matches": out}

@app.post("/score")
def score(req: ScoreReq):
    fx = req.fx_jpy_sgd or FEES["fx_jpy_sgd"]
    gst = req.gst_rate or FEES["gst_rate"]
    pfee = req.platform_fee_rate or FEES["platform_fee_rate"]
    pay = req.payment_fee_rate or FEES["payment_fee_rate"]
    thr = req.gm_threshold or FEES["min_gm_threshold"]

    scored = []
    for m in req.matches:
        # デモ：sg_id / jp_id に応じて参照価格を仮定（後で入力に含める形に）
        if m.jp_id == "jp_001":
            p25, median = 6.2, 8.5
        else:
            p25, median = 12.0, 16.0
        jp_cost_sgd = m.jp_price_jpy * fx
        ship = estimate_ship_cost(m.weight_g, m.thickness_cm)
        cif = jp_cost_sgd + ship
        gst_amt = cif * gst
        sell_price = median
        platform_fee = sell_price * pfee
        payment_fee = sell_price * pay
        landed = jp_cost_sgd + ship + gst_amt + platform_fee + payment_fee
        gm = max(0.0, (sell_price - landed) / sell_price)
        row = {
            "sg_id": m.sg_id,
            "jp_id": m.jp_id,
            "sell_price_ref": {"p25": p25, "median": median},
            "landed_cost": round(landed, 2),
            "gm": round(gm, 3),
            "jp_url": m.jp_url,
        }
        if row["gm"] >= thr:
            row["score"] = row["gm"]
            scored.append(row)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"scored": scored}
