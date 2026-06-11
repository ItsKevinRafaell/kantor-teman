"""Shared business constants for lifecycle labels and workflow defaults."""

from __future__ import annotations


class LeadStatus:
    SCRAPED = "Scraped"
    CONTACTED = "Contacted"
    REPLIED = "Replied"
    CLOSED_CLIENT = "Closed/Client"
    CLOSED_LOST = "Closed/Lost"

    READY_BLAST = "Siap Blast"
    WA_SENT = "WA Terkirim"
    REPORT_OPENED = "Laporan Dibuka"
    STARTED_READING = "Mulai Membaca"
    READING_SERIOUSLY = "Membaca Serius"
    WARM_PROSPECT = "Prospek Hangat"
    HOT_PROSPECT = "Prospek Panas"
    FOLLOW_UP = "Follow Up"
    PROPOSAL_SENT = "Proposal Dikirim"
    DEAL = "Deal"
    ACTIVE_CLIENT = "Klien Aktif"
    COMPLETED = "Selesai"


LEAD_STATUS_LABELS = {
    LeadStatus.SCRAPED: "Baru Discrape",
    LeadStatus.CONTACTED: "Sudah Dihubungi",
    LeadStatus.REPLIED: "Sudah Membalas",
    LeadStatus.CLOSED_CLIENT: "Klien Aktif",
    LeadStatus.CLOSED_LOST: "Tidak Tertarik",
    "HOT_PROSPECT": LeadStatus.HOT_PROSPECT,
    "REPORT_VIEWED": LeadStatus.REPORT_OPENED,
    "Active Client": "Klien Aktif",
    LeadStatus.READY_BLAST: LeadStatus.READY_BLAST,
    LeadStatus.WA_SENT: LeadStatus.WA_SENT,
    LeadStatus.REPORT_OPENED: LeadStatus.REPORT_OPENED,
    LeadStatus.STARTED_READING: LeadStatus.STARTED_READING,
    LeadStatus.READING_SERIOUSLY: LeadStatus.READING_SERIOUSLY,
    LeadStatus.WARM_PROSPECT: LeadStatus.WARM_PROSPECT,
    LeadStatus.HOT_PROSPECT: LeadStatus.HOT_PROSPECT,
    LeadStatus.FOLLOW_UP: LeadStatus.FOLLOW_UP,
    LeadStatus.PROPOSAL_SENT: LeadStatus.PROPOSAL_SENT,
    LeadStatus.DEAL: LeadStatus.DEAL,
    LeadStatus.ACTIVE_CLIENT: LeadStatus.ACTIVE_CLIENT,
    LeadStatus.COMPLETED: LeadStatus.COMPLETED,
}


CLIENT_STATUS_VALUES = {
    LeadStatus.CLOSED_CLIENT,
    LeadStatus.ACTIVE_CLIENT,
    "Active Client",
    LeadStatus.DEAL,
}


class ProposalStatus:
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REPORT = "Report"

    DRAFT_LABEL = "Draft"
    SENT_LABEL = "Dikirim"
    VIEWED_LABEL = "Dilihat"
    ACCEPTED_LABEL = "Diterima"
    REJECTED_LABEL = "Ditolak"
    EXPIRED_LABEL = "Kadaluarsa"


PROPOSAL_STATUS_LABELS = {
    ProposalStatus.SENT: ProposalStatus.SENT_LABEL,
    ProposalStatus.ACCEPTED: ProposalStatus.ACCEPTED_LABEL,
    ProposalStatus.REJECTED: ProposalStatus.REJECTED_LABEL,
    ProposalStatus.REPORT: "Laporan",
}


class DocumentStatus:
    DRAFT = "Draft"
    REVIEW = "Menunggu Review"
    APPROVED = "Disetujui"
    REJECTED = "Ditolak"
    SENT = "Dikirim"
    SIGNED = "Ditandatangani"
    ARCHIVED = "Diarsipkan"


DOCUMENT_STATUSES = {
    DocumentStatus.DRAFT,
    DocumentStatus.REVIEW,
    DocumentStatus.APPROVED,
    DocumentStatus.REJECTED,
    DocumentStatus.SENT,
    DocumentStatus.SIGNED,
    DocumentStatus.ARCHIVED,
}


class PaymentStatus:
    UNPAID = "Belum Dibayar"
    PARTIAL = "Dibayar Sebagian"
    PAID = "Lunas"


PAYMENT_STATUSES = {PaymentStatus.UNPAID, PaymentStatus.PARTIAL, PaymentStatus.PAID}


DEFAULT_SCORING_SETTINGS = {
    "base_score": 50,
    "google_rating_high": 15,
    "google_rating_medium": 10,
    "google_rating_low": 5,
    "google_rating_bad": -10,
    "reviews_high": 15,
    "reviews_medium": 10,
    "website_for_seo": 5,
    "website_not_needed": -5,
    "no_website_for_web": 10,
    "warm_source": 20,
    "cold_source": -5,
    "replied": 15,
    "contacted_no_reply": -10,
    "tier_one_city": 5,
    "company_signal": 10,
    "ai_analysis": 10,
    "report_opened": 10,
    "report_started_reading": 12,
    "report_reading_seriously": 18,
    "report_hot_action": 25,
}


REPORT_ENGAGEMENT_TIERS = [
    (120, LeadStatus.READING_SERIOUSLY),
    (60, LeadStatus.READING_SERIOUSLY),
    (15, LeadStatus.STARTED_READING),
    (0, LeadStatus.REPORT_OPENED),
]


def lead_status_label(status: str | None) -> str:
    return LEAD_STATUS_LABELS.get(status or "", status or "")


def proposal_status_label(status: str | None) -> str:
    return PROPOSAL_STATUS_LABELS.get(status or "", status or "")
