"""Tests for checklist delete + auto-done-to-Done behavior (feat/nara-erp-fixes)."""
import uuid
from app.services import board_service
from models import Board, BoardColumn, BoardCard, BoardCardChecklist, Project


def _mk_board(db, columns):
    proj = Project(id=str(uuid.uuid4()), name="T", type="FIXED", status="ACTIVE")
    db.add(proj)
    board = Board(id=str(uuid.uuid4()), project_id=proj.id)
    db.add(board)
    cols = {}
    for i, name in enumerate(columns):
        c = BoardColumn(id=str(uuid.uuid4()), board_id=board.id, name=name, position=i)
        db.add(c)
        cols[name] = c
    db.commit()
    return board, cols


def _mk_card(db, col, title="card"):
    card = BoardCard(id=str(uuid.uuid4()), column_id=col.id, title=title, position=0)
    db.add(card)
    db.commit()
    return card


def _add_item(db, card, text, done=False):
    it = BoardCardChecklist(id=str(uuid.uuid4()), card_id=card.id, text=text, is_done=done, position=0)
    db.add(it)
    db.commit()
    return it


def test_delete_checklist_item(db):
    _, cols = _mk_board(db, ["To Do", "Done"])
    card = _mk_card(db, cols["To Do"])
    it = _add_item(db, card, "task1")
    board_service.delete_checklist_item(db, card.id, it.id, "tester")
    remaining = db.query(BoardCardChecklist).filter_by(card_id=card.id).all()
    assert remaining == []


def test_delete_checklist_item_not_found(db):
    _, cols = _mk_board(db, ["To Do", "Done"])
    card = _mk_card(db, cols["To Do"])
    try:
        board_service.delete_checklist_item(db, card.id, "nope", "tester")
        assert False, "should raise"
    except ValueError:
        pass


def test_autodone_from_in_progress(db):
    _, cols = _mk_board(db, ["To Do", "In Progress", "Review", "Done"])
    card = _mk_card(db, cols["In Progress"])
    i1 = _add_item(db, card, "a")
    i2 = _add_item(db, card, "b")
    board_service.toggle_checklist_item(db, card.id, i1.id, True, "tester")
    db.refresh(card)
    assert card.column_id == cols["In Progress"].id  # not all done yet
    board_service.toggle_checklist_item(db, card.id, i2.id, True, "tester")
    db.refresh(card)
    assert card.column_id == cols["Done"].id  # all done -> moved


def test_autodone_skips_custom_column(db):
    _, cols = _mk_board(db, ["To Do", "In Progress", "Done", "Maintenance"])
    card = _mk_card(db, cols["Maintenance"])
    i1 = _add_item(db, card, "a")
    board_service.toggle_checklist_item(db, card.id, i1.id, True, "tester")
    db.refresh(card)
    assert card.column_id == cols["Maintenance"].id  # custom col NOT auto-moved


def test_no_autodone_with_no_items(db):
    _, cols = _mk_board(db, ["To Do", "Done"])
    card = _mk_card(db, cols["To Do"])
    # toggle a phantom is impossible; ensure a card with items partially done stays
    i1 = _add_item(db, card, "a")
    i2 = _add_item(db, card, "b")
    board_service.toggle_checklist_item(db, card.id, i1.id, True, "tester")
    db.refresh(card)
    assert card.column_id == cols["To Do"].id


def test_untick_stays_in_done(db):
    _, cols = _mk_board(db, ["To Do", "Done"])
    card = _mk_card(db, cols["To Do"])
    i1 = _add_item(db, card, "a")
    board_service.toggle_checklist_item(db, card.id, i1.id, True, "tester")
    db.refresh(card)
    assert card.column_id == cols["Done"].id
    # untick -> card must stay in Done (Kevin's decision)
    board_service.toggle_checklist_item(db, card.id, i1.id, False, "tester")
    db.refresh(card)
    assert card.column_id == cols["Done"].id
