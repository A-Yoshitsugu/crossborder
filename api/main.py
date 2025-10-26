# api/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# ==== health ====
@app.get("/health")
def health():
    return {"ok": True}

# ==== sg_demand (GET) ====
@app.get("/sg_demand")
def sg_demand(cats: str, days: int = 30):
    # まずはダミーデータ
    items = [
        {"sg_id":"sg_123","title":"Washi Tape Sakura","brand":"BrandA",
         "attrs":{"material":"paper","width_mm":15},"price_p25":6.2,"price_median":8.5,
         "reviews_30d":74,"demand_index":0.78,"comp_intensity":0.35},
        {"sg_id":"sg_456","title":"Tenugui A","brand":"BrandB",
         "attrs":{"material":"cotton"},"price_p25":12.0,"price_median":16.0,
         "reviews_30d":21,"demand_index":0.52,"comp_intensity":0.20},
    ]
    return {"items": items}

# ==== match (POST) ====
class SgItem(BaseModel):
    sg_id: str
    title: Optional[str] = None
    price_p25: Optional[float] = None
    price_median: Optional[float] = None

class MatchReq(BaseModel):
    sg_items: List[SgItem]

@app.post("/match")
def match(req: MatchReq):
    # ダミー：常に jp_001 を返す
    out = []
    for it in req.sg_items:
        out.append({
            "sg_id": it.sg_id,
            "jp_id": "jp_001",
            "jp_price_jpy": 220.0,
            "sim_text": 0.95,
            "weight_g": 40.0,
            "thickness_cm": 2.0,
            "jp_url": "https://example.jp/item/1",
        })
    return {"matches": out}

# ==== score (POST) ====
class MatchRow(BaseModel):
    sg_id: str
    jp_id: str
    jp_price_jpy: float
    sim_text: Optional[float] = None
    weight_g: Optional[float] = 40.0
    thickness_cm: Optional[float] = 2.0
    jp_url: Optional[str] = None

class ScoreReq(BaseModel):
    matches: List[MatchRow]
    fx_jpy_sgd: Optional[float] = 0.009  # 例: 1JPY=0.009SGD
    gst_rate: Optional[float] = 0.08
    platform_fee_rate: Optional[float] = 0.08
    payment_fee_rate: Optional[float] = 0.035
    gm_threshold: Optional[float] = 0.5

def estimate_ship_cost(weight_g: float = 40.0, thickness_cm: float = 2.0) -> float:
    return 2.2  # デモ固定

@app.post("/score")
def score(req: ScoreReq):
    scored = []
    for m in req.matches:
        # デモの売価参照
        if m.jp_id == "jp_001":
            p25, median = 6.2, 8.5
        else:
            p25, median = 12.0, 16.0

        jp_cost_sgd = m.jp_price_jpy * req.fx_jpy_sgd
        ship = estimate_ship_cost(m.weight_g, m.thickness_cm)
        cif = jp_cost_sgd + ship
        gst_amt = cif * req.gst_rate
        platform_fee = median * req.platform_fee_rate
        payment_fee = median * req.payment_fee_rate
        landed = jp_cost_sgd + ship + gst_amt + platform_fee + payment_fee
        gm = max(0.0, (median - landed) / median)

        row = {
            "sg_id": m.sg_id,
            "jp_id": m.jp_id,
            "sell_price_ref": {"p25": p25, "median": median},
            "landed_cost": round(landed, 2),
            "gm": round(gm, 3),
            "jp_url": m.jp_url,
        }
        if row["gm"] >= req.gm_threshold:
            row["score"] = row["gm"]
            scored.append(row)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"scored": scored}
