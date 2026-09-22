# Circles member pages

`MemberMobileHome.tsx` (`/community-circles/members/:id`) is a **staff-assisted view**,
not a real member self-service login. Staff opens it on behalf of a member (e.g. by
clicking a row in the Member Roster table on the Community Circles admin page) to show
that member's status, ledger, and help content on a phone-width layout.

There is currently no `investor_member`-style self-login role, so the route has no
role restriction — any authenticated staff user can open any member's page. When real
member self-service login is built, this route should be gated so a member can only
view their own record.
