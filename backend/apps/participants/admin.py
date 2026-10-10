from django.contrib import admin

from .models import Participant, ParticipantAccount

admin.site.register(Participant)
admin.site.register(ParticipantAccount)
