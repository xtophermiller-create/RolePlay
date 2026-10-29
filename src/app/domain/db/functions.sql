
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$function$;


CREATE OR REPLACE FUNCTION public.users_nickname_default()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    IF NEW.nickname IS NULL OR btrim(NEW.nickname) = '' THEN
        NEW.nickname = left(NEW.login, 32);
    END IF;

    RETURN NEW;
END;
$function$;
