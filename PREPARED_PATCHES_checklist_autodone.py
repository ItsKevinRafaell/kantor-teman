# KantorTeman ERP — Prepared backend patches (AWAIT KEVIN/nara APPROVAL — NOT applied)
# Repo: /root/projects/kantorteman/backend
# Branch workflow: main is READ-ONLY. Create feat/nara-checklist-delete-autodone,
#   acquire repo lock, let raka merge to main + deploy.
# Both changes below are LOGIC-ONLY (no DB migration / no DDL) -> safe to deploy.

# ==========================================================================
# PATCH 1 — BUG FIX: "checklist ga bisa dihapus"
# Root cause: there is NO delete-checklist endpoint. Only POST (add) + PATCH (toggle) exist.
#   Live openapi confirms: /api/board-cards/{card_id}/checklist -> [post]
#                          /api/board-cards/{card_id}/checklist/{item_id} -> [patch]
# The frontend delete button (if any) 404s / no-ops because the route doesn't exist.
#
# FIX A — service fn, append to app/services/board_service.py after toggle_checklist_item():
# --------------------------------------------------------------------------
def delete_checklist_item(
    db,           # Session
    card_id: str,
    item_id: str,
    actor: str,
) -> None:
    item = db.query(BoardCardChecklist).filter(
        BoardCardChecklist.id == item_id,
        BoardCardChecklist.card_id == card_id,
    ).first()
    if not item:
        raise ValueError("Checklist item tidak ditemukan")
    text = item.text
    db.delete(item)
    activity = BoardCardActivity(
        id=str(uuid.uuid4()),
        card_id=card_id,
        action="checklist",
        description=f'Checklist "{text}" dihapus',
        actor=actor,
    )
    db.add(activity)
    db.commit()

# Also export it in app/services/__init__.py alongside toggle_checklist_item.

# FIX B — route, add to routers/other.py right after update_card_checklist (PATCH, ~L280):
# --------------------------------------------------------------------------
@router.delete("/api/board-cards/{card_id}/checklist/{item_id}", status_code=204)
def delete_card_checklist(card_id: str, item_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Hapus checklist item dari card."""
    try:
        board_service.delete_checklist_item(db, card_id, item_id, current_user.name)
    except (ValueError, PermissionError) as exc:
        _raise_board_http_error(exc)

# RISK: LOW. Additive endpoint, no schema/DB change, mirrors existing attachment-delete
#   pattern. Reversible (remove route). Frontend may also need a delete button wired to it
#   (check frontend board card component) — but the API gap is the primary blocker.


# ==========================================================================
# PATCH 2 — FEATURE: auto-move card to "Done" when ALL checklist items complete
# Current: toggle_checklist_item() only flips is_done, never touches the card's column.
# Proposed: after a toggle, if the card has >=1 checklist item AND all are done,
#   move it to the board's "Done" column automatically. (And OPTIONAL: move it back
#   out of Done if an item is un-ticked — decide with Kevin.)
#
# Insert into toggle_checklist_item() in board_service.py, BEFORE the final
# db.commit()/db.refresh (replace the existing tail), after item.is_done = is_done:
# --------------------------------------------------------------------------
#   ... existing activity add ...
#   db.add(activity)
#
#   # AUTO-DONE: if every checklist item on this card is now done, move card to Done column
#   card = db.query(BoardCard).filter(BoardCard.id == card_id).first()
#   if card:
#       items = db.query(BoardCardChecklist).filter(BoardCardChecklist.card_id == card_id).all()
#       if items and all(i.is_done for i in items):
#           col = db.query(BoardColumn).filter(BoardColumn.id == card.column_id).first()
#           if col:
#               done_col = db.query(BoardColumn).filter(
#                   BoardColumn.board_id == col.board_id,
#                   func.lower(BoardColumn.name) == "done",
#               ).first()
#               if done_col and card.column_id != done_col.id:
#                   card.column_id = done_col.id
#                   db.add(BoardCardActivity(
#                       id=str(uuid.uuid4()), card_id=card_id, action="move",
#                       description="Card otomatis dipindah ke Done (semua checklist selesai)",
#                       actor="system",
#                   ))
#       # OPTIONAL reverse rule (confirm with Kevin before enabling):
#       # elif not is_done and card is currently in Done: move back to In Progress
#   db.commit()
#   db.refresh(item)
#   return _board_card_checklist_to_out(item)
#
# Requires importing func (from sqlalchemy) + BoardColumn in board_service.py if not present.
#
# RISK: MEDIUM. Changes existing behaviour of a hot path (every checklist toggle).
#   Edge cases to confirm with Kevin:
#   - Cards with ZERO checklist items are untouched (guard `if items` handles this).
#   - A card manually parked in To Do with all-done checklist WILL jump to Done on next toggle.
#     Currently 2 MHK cards are all-done-but-not-in-Done (Technical SEO maintenance 12/12 in
#     In Progress; Maintenance rutin bulanan 3/3 in Maintenance col). With this rule they'd
#     move to Done on the next toggle — but "Maintenance rutin bulanan" living in the
#     "Maintenance" column ON PURPOSE would get yanked to Done. => Kevin may want auto-done
#     to apply ONLY from To Do/In Progress/Review, NOT from custom cols (Maintenance,
#     Artikel/LP Bulanan). Recommend: skip auto-done if current column not in
#     {To Do, In Progress, Review}. Confirm before shipping.
#   - Reversible: remove the block.
