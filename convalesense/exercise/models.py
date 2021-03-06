from __future__ import unicode_literals, division

from django.db import models
from django.utils.html import mark_safe
from django.template.defaultfilters import date as date_fmt


from .managers import EnabledManager
from ..users.models import User


class BaseModel(models.Model):
    TAG_CHOICES = (
        ('a', 'Android'),
        ('i', 'iOS')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    enabled = models.BooleanField(default=True)

    tag = models.CharField(max_length=1, choices=TAG_CHOICES, blank=True, null=True)
    tag.help_text = 'Used to filter this to a particular platform if required (for Demo)'

    published = EnabledManager()
    objects = models.Manager()

    class Meta:
        abstract = True
        ordering = ('-updated_at', '-created_at',)


class AbstractExercise(BaseModel):
    number_of_reps = models.PositiveSmallIntegerField(blank=True, null=True)
    number_of_reps.help_text = 'How many times to do this'
    distance = models.FloatField(blank=True, null=True)
    distance.help_text = 'Through distance in meters'
    duration = models.PositiveSmallIntegerField(blank=True, null=True)
    duration.help_text = 'Time in seconds for this exercise'
    score = models.PositiveSmallIntegerField(blank=True, null=True)
    score.help_text = 'Score for this exercise per rep'
    weight = models.FloatField(blank=True, null=True)
    weight.help_text = 'Weight of object in kilograms'

    class Meta:
        abstract = True


class Exercise(AbstractExercise):
    EXERCISE_TYPES = (
        ('t', 'Duration'),
        ('d', 'Distance'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    steps = models.TextField(blank=True, null=True)
    steps.help_text = 'If you would like to add a step by step guide for this exercise list it here'
    type_of_exercise = models.CharField(choices=EXERCISE_TYPES, max_length=1)
    type_of_exercise.help_text = 'Particular game type - this determines what is presented back to the users app'
    image = models.ImageField(upload_to='images', blank=True, null=True)

    def record_count(self):
        return sum([plan.record_count for plan in self.plan_set.all()])

    def __unicode__(self):
        return self.name


class Plan(BaseModel):
    patient = models.ForeignKey(User, related_name='patient')
    patient.help_text = 'Choose who this plan is for'
    therapist = models.ForeignKey(User, related_name='therapist')
    therapist.help_text = 'Choose a therapist overseeing this treatment plan'
    exercises = models.ManyToManyField(Exercise, through='PlanExercise', through_fields=('plan', 'exercise'))
    name = models.CharField(max_length=100, null=True, blank=True)
    name.help_text = 'Name of this plan as displayed to the patient'
    description = models.TextField(blank=True, null=True)
    description.help_text = 'What this plan aims to achieve for the patient'
    exercises.help_text = 'A plan is composed of multiple exercises which may be in order'
    session_count = models.PositiveSmallIntegerField(default=1, blank=True, null=True)
    session_count.help_text = 'How often the patient should do this plan daily'
    start = models.DateTimeField(blank=True, null=True)
    start.help_text = 'When this treatment plan begins'
    end = models.DateTimeField(blank=True, null=True)
    end.help_text = 'When this treatment plan ends, if at all'
    image = models.ImageField(upload_to='images', blank=True, null=True)

    class Meta:
        ordering = ('start', '-updated_at')

    @property
    def record_count(self):
        return sum([ex.exerciserecord_set.count() for ex in self.planexercise_set.all()])

    @property
    def exercise_count(self):
        return self.exercises.count()

    def __unicode__(self):
        return 'Plan {:3d} ({}) for {} by {}'.format(self.id, self.name, self.patient, self.therapist)


class PlanExercise(AbstractExercise):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    exercise.help_text = 'Select an exercise to use as a basis for this plan'
    additional_description = models.TextField(blank=True, null=True)
    additional_description.help_text = 'Add any patient specific information for this exercise. It will be appended to the instructions'
    order = models.PositiveSmallIntegerField(blank=True, null=True)
    order.help_text = 'You can use this to customize the order this exercise appears in the plan'
    count = models.PositiveSmallIntegerField(default=1)
    count.help_text = 'How many times this exercise should be done per day'
    optional = models.BooleanField(default=False)
    optional.help_text = 'Whether or not this exercise is a required part of the plan for completeness'
    image = models.ImageField(upload_to='images', blank=True, null=True)

    @property
    def name(self):
        return self.exercise.name

    @property
    def reps(self):
        return self.number_of_reps if self.number_of_reps else self.exercise.number_of_reps

    @property
    def guidelines(self):
        optional_label = 'optional' if self.optional else 'required'

        plural = 's'
        if self.count == 1:
            plural = ''

        if self.weight:
            prefix = 'Lift a {}kg weight '.format(self.weight)
        elif self.exercise.weight:
            prefix = 'Lift a {}kg weight '.format(self.exercise.weight)
        else:
            prefix = ''

        return mark_safe('{}{} time{} per day with {} reps per session. This exercise is {}.'.format(
                prefix, self.count, plural, self.reps, optional_label))

    class Meta:
        ordering = ('order', 'exercise__name')

    def __unicode__(self):
        return unicode(self.exercise)


class ExerciseRecord(BaseModel):
    exercise = models.ForeignKey(PlanExercise)
    count = models.PositiveSmallIntegerField()
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        ordering = ('-updated_at', '-created_at')

    @property
    def natural_date(self):
        return '<span>{}</span><span>{}</span>'.format(
            self.start.date(),
            date_fmt(self.start, 'F jS'))

    @property
    def completed_time(self):
        return self.end - self.start

    @property
    def percentage(self):
        return (self.count / self.exercise.reps) * 100

    def __unicode__(self):
        return '{} - {} in {} on {}'.format(self.exercise, self.count, self.completed_time, self.start)

    class Meta:
        unique_together = ('exercise', 'start')
        ordering = ('start', 'end')

