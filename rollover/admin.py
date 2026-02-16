from django.contrib import admin
from .models import Rollover, RolloverRound
@admin.register(Rollover)
class RolloverAdmin(admin.ModelAdmin):
    list_display = ('id','name','currency','initial_stake','target_odds','reinvest_pct','total_rounds','status','current_bankroll','created_at')
    search_fields = ('name',)
@admin.register(RolloverRound)
class RolloverRoundAdmin(admin.ModelAdmin):
    list_display = ('id','rollover','number','status','planned_stake','planned_odds','actual_stake','actual_odds','return_amount','bankroll_after')
    list_filter = ('status','pick_type')
