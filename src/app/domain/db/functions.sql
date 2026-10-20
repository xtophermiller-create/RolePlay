
CREATE OR REPLACE FUNCTION public.room_roles_ok(
    host_id integer,
    player_ids integer[],
    actor1_id integer,
    actor2_id integer,
    observer_ids integer[]
)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $function$
    SELECT
        array_position(player_ids, NULL) IS NULL
        AND array_position(observer_ids, NULL) IS NULL
        AND host_id = ANY (player_ids)
        AND (actor1_id IS NULL OR actor1_id = ANY (player_ids))
        AND (actor2_id IS NULL OR actor2_id = ANY (player_ids))
        AND observer_ids <@ player_ids
        AND (actor1_id IS NULL OR NOT actor1_id = ANY (observer_ids))
        AND (actor2_id IS NULL OR NOT actor2_id = ANY (observer_ids))
        AND (actor1_id IS NULL OR actor2_id IS NULL OR actor1_id <> actor2_id)
        AND (
            SELECT count(*) = count(DISTINCT user_id)
            FROM unnest(player_ids) AS user_id
        )
        AND (
            SELECT count(*) = count(DISTINCT user_id)
            FROM unnest(observer_ids) AS user_id
        )
        AND (
            SELECT bool_and(
                user_id = host_id
                OR user_id IS NOT DISTINCT FROM actor1_id
                OR user_id IS NOT DISTINCT FROM actor2_id
                OR user_id = ANY (observer_ids)
            )
            FROM unnest(player_ids) AS user_id
        );
$function$;


CREATE OR REPLACE FUNCTION public.rooms_forbid_delete_while_live()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    IF OLD.status = 'in_session' OR OLD.session_id IS NOT NULL THEN
        RAISE EXCEPTION 'room_has_live_session';
    END IF;

    RETURN OLD;
END;
$function$;


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
