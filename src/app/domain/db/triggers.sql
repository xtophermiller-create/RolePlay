
DROP TRIGGER IF EXISTS rooms_forbid_delete_while_live ON public.rooms;
CREATE TRIGGER rooms_forbid_delete_while_live
BEFORE DELETE ON public.rooms
FOR EACH ROW
EXECUTE FUNCTION public.rooms_forbid_delete_while_live();


DROP TRIGGER IF EXISTS rooms_set_updated_at ON public.rooms;
CREATE TRIGGER rooms_set_updated_at
BEFORE UPDATE ON public.rooms
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();


DROP TRIGGER IF EXISTS scenarios_set_updated_at ON public.scenarios;
CREATE TRIGGER scenarios_set_updated_at
BEFORE UPDATE ON public.scenarios
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();


DROP TRIGGER IF EXISTS users_nickname_default ON public.users;
CREATE TRIGGER users_nickname_default
BEFORE INSERT ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.users_nickname_default();


DROP TRIGGER IF EXISTS users_set_updated_at ON public.users;
CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();
