

def create_session(
        *,
        owner_id: int | None = None,
        actor1_id: int | None = None,
        actor2_id: int | None = None,
        observer_ids: list[int] | None = None,
        player_ids: list[int] | None = None,
        title: str | None = None,
        format_version: int | None = None,
        actor1: str | None = None,
        actor2: str | None = None,
        target1: str | None = None,
        target2: str | None = None,
        context1: str | None = None,
        context2: str | None = None,
        doc1: dict | None = None,
        doc2: dict | None = None,
):
    return