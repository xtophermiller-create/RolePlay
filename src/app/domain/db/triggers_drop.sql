DROP TRIGGER IF EXISTS rooms_forbid_delete_while_live ON public.rooms;
DROP TRIGGER IF EXISTS rooms_set_updated_at ON public.rooms;
DROP TRIGGER IF EXISTS scenarios_set_updated_at ON public.scenarios;
DROP TRIGGER IF EXISTS users_nickname_default ON public.users;
DROP TRIGGER IF EXISTS users_set_updated_at ON public.users;