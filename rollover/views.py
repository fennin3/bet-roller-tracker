import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from .models import Rollover, RolloverRound


def index(request):
    rollovers = Rollover.objects.order_by("-created_at")[:20]
    return render(request, "rollover/index.html", {"rollovers": rollovers})


@require_http_methods(["POST"])
def rollover_delete(request, rollover_id):
    r = get_object_or_404(Rollover, id=rollover_id)
    r.delete()
    return redirect("index")


def _generate_rounds(rollover):
    bankroll = rollover.initial_stake
    for i in range(1, rollover.total_rounds + 1):
        stake_this = Decimal(bankroll) * Decimal(rollover.reinvest_pct) / Decimal(100)
        return_this = Decimal(stake_this) * Decimal(rollover.target_odds)
        carry = Decimal(bankroll) - Decimal(stake_this) + Decimal(return_this)
        RolloverRound.objects.create(
            rollover=rollover,
            number=i,
            planned_stake=stake_this,
            planned_odds=rollover.target_odds,
            bankroll_after=carry,
        )
        bankroll = carry
    rollover.current_bankroll = bankroll
    rollover.save()


@require_http_methods(["POST"])
def rollover_create(request):
    name = request.POST.get("name") or "My Rollover"
    currency = request.POST.get("currency") or "GHS"
    initial_stake = request.POST.get("initial_stake") or "100"
    target_odds = request.POST.get("target_odds") or "2.0"
    reinvest_pct = int(request.POST.get("reinvest_pct") or "100")
    total_rounds = int(request.POST.get("total_rounds") or "3")
    r = Rollover.objects.create(
        name=name,
        currency=currency,
        initial_stake=Decimal(initial_stake),
        target_odds=Decimal(target_odds),
        reinvest_pct=reinvest_pct,
        total_rounds=total_rounds,
        status="active",
    )
    _generate_rounds(r)
    return redirect("rollover_detail", rollover_id=r.id)


def rollover_detail(request, rollover_id):
    r = get_object_or_404(Rollover, id=rollover_id)
    rounds = list(r.rounds.all())
    return render(
        request, "rollover/rollover_detail.html", {"rollover": r, "rounds": rounds}
    )


def _norm_probs(odds):
    oh = Decimal(odds.get("home") or 0)
    od = Decimal(odds.get("draw") or 0)
    oa = Decimal(odds.get("away") or 0)
    rh = Decimal(1) / oh if oh else Decimal(0)
    rd = Decimal(1) / od if od else Decimal(0)
    ra = Decimal(1) / oa if oa else Decimal(0)
    s = rh + rd + ra
    if s == 0:
        return {"ph": 0, "pd": 0, "pa": 0}
    return {"ph": float(rh / s), "pd": float(rd / s), "pa": float(ra / s)}


def _lambda_from_probs(p):
    base = 2.2
    adj = max(min(base - 1.5 * p["pd"], 3.5), 0.4)
    return adj


@require_http_methods(["GET"])
def api_recommendations(request):
    pick = request.GET.get("pick_type") or "dc_1x"
    min_odds = float(request.GET.get("min_odds") or "1.2")
    max_odds = float(request.GET.get("max_odds") or "2.5")
    min_prob = float(request.GET.get("min_prob") or "70")
    try:
        with open((timezone.now(),), "rb"):
            pass
    except Exception:
        pass
    try:
        path = request.GET.get("path") or "rollover/static/rollover/matches.sample.json"
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        try:
            with open("matches.sample.json", "r") as f:
                data = json.load(f)
        except Exception:
            data = []
    target = float(request.GET.get("target_odds") or "2.0")
    recs = []
    for m in data:
        odds = m.get("odds") or {}
        p = _norm_probs(odds)
        ip = 0.0
        dec = 0.0
        ok = False
        if pick == "result_home" and odds.get("home"):
            dec = float(odds["home"])
            ip = 100 / dec
            ok = dec >= min_odds and dec <= max_odds and ip >= min_prob
        elif pick == "result_draw" and odds.get("draw"):
            dec = float(odds["draw"])
            ip = 100 / dec
            ok = dec >= min_odds and dec <= max_odds and ip >= min_prob
        elif pick == "result_away" and odds.get("away"):
            dec = float(odds["away"])
            ip = 100 / dec
            ok = dec >= min_odds and dec <= max_odds and ip >= min_prob
        elif pick == "dc_1x":
            prob = p["ph"] + p["pd"]
            ip = prob * 100
            dec = 1 / max(prob, 1e-9)
            ok = dec >= min_odds and dec <= max_odds and ip >= min_prob
        elif pick == "dc_x2":
            prob = p["pa"] + p["pd"]
            ip = prob * 100
            dec = 1 / max(prob, 1e-9)
            ok = dec >= min_odds and dec <= max_odds and ip >= min_prob
        elif pick == "goals_over_0_5":
            lam = _lambda_from_probs(p)
            prob = 1 - (2.718281828459045) ** (-lam)
            ip = prob * 100
            dec = 1 / max(prob, 1e-9)
            ok = dec >= min_odds and dec <= max_odds and ip >= min_prob
        elif pick == "goals_over_1_5":
            lam = _lambda_from_probs(p)
            prob = 1 - (2.718281828459045) ** (-lam) * (1 + lam)
            ip = prob * 100
            dec = 1 / max(prob, 1e-9)
            ok = dec >= min_odds and dec <= max_odds and ip >= min_prob
        elif pick == "goals_even":
            lam = _lambda_from_probs(p)
            prob = 0.5 * (1 + (2.718281828459045) ** (-2 * lam))
            ip = prob * 100
            dec = 1 / max(prob, 1e-9)
            ok = dec >= min_odds and dec <= max_odds and ip >= min_prob
        if ok:
            recs.append(
                {
                    "id": m.get("id"),
                    "league": m.get("league"),
                    "starts_at": m.get("starts_at"),
                    "home": m.get("home"),
                    "away": m.get("away"),
                    "pick_type": pick,
                    "odds": round(dec, 2),
                    "prob": round(ip, 2),
                    "score": abs(dec - target),
                }
            )
    recs.sort(key=lambda x: (x["score"], x["starts_at"] or ""))
    return JsonResponse({"results": recs[:20]})


@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def api_round_update(request, round_id):
    r = get_object_or_404(RolloverRound, id=round_id)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("invalid json")
    status = data.get("status") or r.status
    r.status = status
    if data.get("actual_stake") is not None:
        r.actual_stake = Decimal(str(data.get("actual_stake")))
    if data.get("actual_odds") is not None:
        r.actual_odds = Decimal(str(data.get("actual_odds")))
    if data.get("games_count") is not None:
        try:
            r.games_count = int(data.get("games_count") or 0)
        except Exception:
            r.games_count = r.games_count
    if data.get("notes") is not None:
        r.notes = data.get("notes") or ""
    r.save()
    parent = r.rollover
    bankroll = Decimal(parent.initial_stake)
    for rr in parent.rounds.all():
        stake = Decimal(rr.actual_stake or rr.planned_stake)
        odds = Decimal(rr.actual_odds or rr.planned_odds)
        if rr.status == "won":
            ret = stake * odds
            carry = bankroll - stake + ret
        elif rr.status == "lost":
            ret = Decimal(0)
            carry = bankroll - stake
        elif rr.status == "void":
            ret = Decimal(0)
            carry = bankroll
        else:
            ret = Decimal(0)
            carry = bankroll
        rr.return_amount = ret if rr.status in ["won", "lost"] else None
        rr.bankroll_after = carry
        rr.save()
        bankroll = carry
    parent.current_bankroll = bankroll
    if all(
        rr.status in ["won", "lost", "void", "skipped"] for rr in parent.rounds.all()
    ):
        parent.status = "completed"
    parent.save()
    return JsonResponse(
        {
            "ok": True,
            "rollover_id": parent.id,
            "current_bankroll": float(parent.current_bankroll),
        }
    )


@require_http_methods(["GET"])
def api_rollover_progress(request, rollover_id):
    r = get_object_or_404(Rollover, id=rollover_id)
    rounds = []
    for rr in r.rounds.all():
        rounds.append(
            {
                "id": rr.id,
                "number": rr.number,
                "status": rr.status,
                "planned_stake": float(rr.planned_stake),
                "planned_odds": float(rr.planned_odds),
                "actual_stake": float(rr.actual_stake or 0),
                "actual_odds": float(rr.actual_odds or 0),
                "return_amount": float(rr.return_amount or 0),
                "bankroll_after": float(rr.bankroll_after or 0),
                "pick_type": rr.pick_type,
                "games_count": rr.games_count,
            }
        )
    return JsonResponse(
        {
            "id": r.id,
            "name": r.name,
            "status": r.status,
            "currency": r.currency,
            "current_bankroll": float(r.current_bankroll),
            "rounds": rounds,
        }
    )
