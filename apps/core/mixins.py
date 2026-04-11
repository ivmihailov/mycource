from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404


class OwnerOrStaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    owner_field = "author"

    def test_func(self):
        obj = self.get_object()
        owner = getattr(obj, self.owner_field, None)
        return self.request.user.is_staff or owner == self.request.user


class CourseOwnershipRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        course = self.get_course()
        if not (request.user.is_staff or course.author == request.user):
            raise Http404
        self.course = course
        return super().dispatch(request, *args, **kwargs)
