
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
