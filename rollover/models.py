from django.db import models


class Rollover(models.Model):
    STATUS_CHOICES = [
        ("active", "active"),
        ("completed", "completed"),
        ("cancelled", "cancelled"),
    ]
    name = models.CharField(max_length=120)
    currency = models.CharField(max_length=8, default="GHS")
    initial_stake = models.DecimalField(max_digits=12, decimal_places=2)
    target_odds = models.DecimalField(max_digits=8, decimal_places=2)
    reinvest_pct = models.PositiveIntegerField(default=100)
    total_rounds = models.PositiveIntegerField(default=3)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="active")
    current_bankroll = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.current_bankroll:
            self.current_bankroll = self.initial_stake
        super().save(*args, **kwargs)


class RolloverRound(models.Model):
    STATUS_CHOICES = [
        ("pending", "pending"),
        ("running", "running"),
        ("won", "won"),
        ("lost", "lost"),
        ("void", "void"),
        ("skipped", "skipped"),
    ]
    PICK_CHOICES = [
        ("result_home", "result_home"),
        ("result_draw", "result_draw"),
        ("result_away", "result_away"),
        ("dc_1x", "dc_1x"),
        ("dc_x2", "dc_x2"),
        ("goals_over_0_5", "goals_over_0_5"),
        ("goals_over_1_5", "goals_over_1_5"),
        ("goals_even", "goals_even"),
    ]
    rollover = models.ForeignKey(
        Rollover, on_delete=models.CASCADE, related_name="rounds"
    )
    number = models.PositiveIntegerField()
    planned_stake = models.DecimalField(max_digits=12, decimal_places=2)
    planned_odds = models.DecimalField(max_digits=8, decimal_places=2)
    pick_type = models.CharField(
        max_length=24, choices=PICK_CHOICES, default="result_home"
    )
    games_count = models.PositiveIntegerField(default=1)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    actual_stake = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    actual_odds = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    return_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    bankroll_after = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("rollover", "number")]
        ordering = ["number"]
