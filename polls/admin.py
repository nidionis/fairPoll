from django.contrib import admin
from .models import HousePoll, QuickPoll, HouseBallot, QuickBallot, BallotChoice, Ticket


@admin.register(HousePoll)
class HousePollAdmin(admin.ModelAdmin):
    list_display = ('question_short', 'house', 'poll_type', 'is_ticket_secured', 'dead_line', 'is_finished', 'created_at')
    list_filter = ('poll_type', 'is_ticket_secured', 'created_at', 'house')
    search_fields = ('question', 'house__name')
    readonly_fields = ('created_at', 'is_finished')
    
    def question_short(self, obj):
        return obj.question[:50] + ('...' if len(obj.question) > 50 else '')
    question_short.short_description = 'Question'


@admin.register(QuickPoll)
class QuickPollAdmin(admin.ModelAdmin):
    list_display = ('poll_id', 'question_short', 'is_ticket_secured', 'dead_line', 'is_finished', 'created_at')
    list_filter = ('is_ticket_secured', 'created_at')
    search_fields = ('question', 'poll_id')
    readonly_fields = ('poll_id', 'created_at', 'is_finished')
    
    def question_short(self, obj):
        return obj.question[:50] + ('...' if len(obj.question) > 50 else '')
    question_short.short_description = 'Question'


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('code', 'poll', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at', 'poll__house')
    search_fields = ('code', 'poll__question')
    readonly_fields = ('created_at',)


class BallotChoiceInline(admin.TabularInline):
    model = BallotChoice
    extra = 0
    fields = ('option_index', 'rank')


@admin.register(HouseBallot)
class HouseBallotAdmin(admin.ModelAdmin):
    list_display = ('poll', 'voter', 'ticket', 'created_at')
    list_filter = ('created_at', 'poll__house')
    search_fields = ('poll__question', 'voter__username', 'ticket__code')
    readonly_fields = ('created_at',)
    inlines = [BallotChoiceInline]


@admin.register(QuickBallot)
class QuickBallotAdmin(admin.ModelAdmin):
    list_display = ('poll', 'voter', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('poll__question', 'poll__poll_id', 'voter__username')
    readonly_fields = ('created_at',)
    inlines = [BallotChoiceInline]
