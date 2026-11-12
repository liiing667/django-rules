from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase

from rules.predicates import (
    _context,
    is_active,
    is_authenticated,
    is_group_member,
    is_staff,
    is_superuser,
)

from . import TestData


class SwappedUser(object):
    pass


class PredicateTests(TestData, TestCase):
    def test_is_authenticated(self):
        assert is_authenticated(User.objects.get(username="adrian"))
        assert not is_authenticated(SwappedUser())

    def test_is_superuser(self):
        assert is_superuser(User.objects.get(username="adrian"))
        assert not is_superuser(SwappedUser())

    def test_is_staff(self):
        assert is_staff(User.objects.get(username="adrian"))
        assert not is_staff(SwappedUser())

    def test_is_active(self):
        assert is_active(User.objects.get(username="adrian"))
        assert not is_active(SwappedUser())

    def test_is_group_member(self):
        p1 = is_group_member("somegroup")
        assert p1.name == "is_group_member:somegroup"
        assert p1.num_args == 1

        p2 = is_group_member("g1", "g2", "g3", "g4")
        assert p2.name == "is_group_member:g1,g2,g3,..."

        p = is_group_member("editors")
        assert p(User.objects.get(username="martin"))
        assert not p(SwappedUser())

        p = is_group_member("editors", "staff")
        assert not p(User.objects.get(username="martin"))
        assert not p(SwappedUser())

    def test_is_group_member_reflects_membership_changes(self):
        martin = User.objects.get(username="martin")
        p = is_group_member("editors")

        assert p.test(martin)

        # Privileged group is revoked while the user object is reused.
        martin.groups.remove(Group.objects.get(name="editors"))
        assert not p.test(martin)

        # Re-adding the group must be picked up as well.
        martin.groups.add(Group.objects.get(name="editors"))
        assert p.test(martin)

        # No state must be attached to the user instance itself.
        assert not hasattr(martin, "_group_names_cache")

    def test_is_group_member_does_not_share_cache_between_rules(self):
        martin = User.objects.get(username="martin")
        editors = is_group_member("editors")
        admins = is_group_member("admins")

        Group.objects.create(name="admins")

        assert editors.test(martin)
        assert not admins.test(martin)

        martin.groups.add(Group.objects.get(name="admins"))
        martin.groups.remove(Group.objects.get(name="editors"))

        assert not editors.test(martin)
        assert admins.test(martin)

    def test_is_group_member_reuses_names_within_an_invocation(self):
        martin = User.objects.get(username="martin")
        p = is_group_member("editors")

        with self.assertNumQueries(1):
            assert p.test(martin)

        # Every new invocation re-reads the database.
        with self.assertNumQueries(1):
            assert p.test(martin)

    def test_is_group_member_denies_anonymous_and_groupless_users(self):
        p = is_group_member("editors")
        assert not p.test(AnonymousUser())
        assert not p.test(SwappedUser())

    def test_is_group_member_cache_is_scoped_to_invocation(self):
        martin = User.objects.get(username="martin")
        p = is_group_member("editors")

        # The context store only exists for the duration of the invocation;
        # once it returns nothing survives on the user or in any shared
        # location, so later invocations always re-read the database.
        assert p.test(martin)
        assert _context.stack == []
        assert not hasattr(martin, "_group_names_cache")
