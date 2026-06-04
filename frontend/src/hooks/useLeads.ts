"use client";

import { useState, useCallback } from "react";
import { useApi, apiMutate } from "../lib/swr";
import { apiFetch } from "../lib/api";
import type { Lead } from "../types";

interface Category { id: string; name: string }
interface BlastTemplate { id: string; name: string; content: string; category_id: string | null }
interface LeadFormData { business_name: string; phone_number: string; address: string; product_interest: string }

interface UseLeadsTableReturn {
  leads: Lead[];
  leadsLoading: boolean;
  batches: string[];
  blastTemplates: BlastTemplate[];
  blastCategories: Category[];
  followUpTemplates: BlastTemplate[];
  filters: {
    status: string;
    batch: string;
    score: "" | "hot" | "warm" | "cold";
    rating: number;
  };
  setFilterStatus: (s: string) => void;
  setFilterBatch: (b: string) => void;
  setFilterScore: (s: "" | "hot" | "warm" | "cold") => void;
  setFilterRating: (r: number) => void;
  showArchived: boolean;
  setShowArchived: (v: boolean) => void;
  // Actions
  refresh: () => void;
  recalculate: () => Promise<void>;
  deleteLead: (id: number) => Promise<void>;
  restoreLead: (id: number) => Promise<void>;
  updateStatus: (id: number, status: string) => Promise<void>;
  updateProduct: (id: number, product: string) => Promise<void>;
  deleteBatch: (batchName: string) => Promise<void>;
  startBlast: (batch: string, categoryId: string, minRating: number, templateId: string, sendMode: string, scheduledFor: string) => Promise<void>;
  saveSalesAction: (leadId: number, data: { sales_owner: string; next_action_at: string; loss_reason: string; do_not_contact: boolean }) => Promise<void>;
  convertLead: (id: number) => Promise<void>;
  createLead: (data: LeadFormData) => Promise<void>;
  updateLead: (id: number, data: LeadFormData) => Promise<void>;
}

export function useLeadsTable(initialBatch?: string): UseLeadsTableReturn {
  // SWR hooks
  const { data: leadsData = [], mutate: refreshLeads } = useApi<Lead[]>("/api/leads");
  const { data: batchesData = [] } = useApi<string[]>("/api/leads/batches");
  const { data: templatesData = [] } = useApi<BlastTemplate[]>("/api/dynamic-templates?type=WA_BLAST");
  const { data: followUpData = [] } = useApi<BlastTemplate[]>("/api/dynamic-templates?type=FOLLOW_UP");
  const { data: categoriesData = [] } = useApi<Category[]>("/api/categories?active_only=true");

  // Filter state managed in component but using SWR for data
  const [filters, setFilters] = useState({ status: "", batch: initialBatch || "", score: "" as "hot" | "warm" | "cold" | "", rating: 0 });
  const [showArchived, setShowArchived] = useState(false);

  const refresh = useCallback(() => {
    apiMutate("/api/leads");
    apiMutate("/api/leads/batches");
  }, []);

  const recalculate = useCallback(async () => {
    await apiFetch("/api/leads/recalculate-scores", { method: "POST" });
    refresh();
  }, [refresh]);

  const deleteLead = useCallback(async (id: number) => {
    await apiFetch(`/api/leads/${id}`, { method: "DELETE" });
    refresh();
  }, [refresh]);

  const restoreLead = useCallback(async (id: number) => {
    await apiFetch(`/api/leads/restore/${id}`, { method: "POST" });
    refresh();
  }, [refresh]);

  const updateStatus = useCallback(async (id: number, status: string) => {
    await apiFetch(`/api/leads/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
    refresh();
  }, [refresh]);

  const updateProduct = useCallback(async (id: number, product: string) => {
    await apiFetch(`/api/leads/${id}/product`, { method: "PATCH", body: JSON.stringify({ product_interest: product }) });
    refresh();
  }, [refresh]);

  const deleteBatch = useCallback(async (batchName: string) => {
    await apiFetch(`/api/leads/batch/${encodeURIComponent(batchName)}`, { method: "DELETE" });
    apiMutate("/api/leads/batches");
    refresh();
  }, [refresh]);

  const startBlast = useCallback(async (batch: string, categoryId: string, minRating: number, templateId: string, sendMode: string, scheduledFor: string) => {
    const payload: Record<string, unknown> = {
      batch_name: batch,
      template_id: templateId,
      filter_criteria: { status: "Scraped", batch_name: batch, min_rating: minRating },
    };
    if (sendMode === "scheduled") {
      payload.scheduled_for = new Date(scheduledFor).toISOString();
      await apiFetch("/api/campaign/blast/schedule", { method: "POST", body: JSON.stringify(payload) });
    } else {
      await apiFetch("/api/campaign/blast", { method: "POST", body: JSON.stringify(payload) });
      localStorage.setItem("blast_batch", batch);
    }
  }, []);

  const saveSalesAction = useCallback(async (leadId: number, data: { sales_owner: string; next_action_at: string; loss_reason: string; do_not_contact: boolean }) => {
    await apiFetch(`/api/leads/${leadId}/sales`, {
      method: "PATCH",
      body: JSON.stringify({ ...data, next_action_at: data.next_action_at ? new Date(data.next_action_at).toISOString() : null }),
    });
    refresh();
  }, [refresh]);

  const convertLead = useCallback(async (id: number) => {
    await apiFetch(`/api/leads/${id}/convert`, { method: "POST" });
    refresh();
  }, [refresh]);

  const createLead = useCallback(async (data: LeadFormData) => {
    await apiFetch("/api/leads", { method: "POST", body: JSON.stringify(data) });
    refresh();
  }, [refresh]);

  const updateLead = useCallback(async (id: number, data: LeadFormData) => {
    await apiFetch(`/api/leads/${id}`, { method: "PUT", body: JSON.stringify(data) });
    refresh();
  }, [refresh]);

  return {
    leads: leadsData,
    leadsLoading: leadsData === undefined,
    batches: batchesData,
    blastTemplates: templatesData,
    blastCategories: categoriesData,
    followUpTemplates: followUpData,
    filters,
    setFilterStatus: (s: string) => setFilters(f => ({ ...f, status: s })),
    setFilterBatch: (b: string) => setFilters(f => ({ ...f, batch: b })),
    setFilterScore: (s: "hot" | "warm" | "cold" | "") => setFilters(f => ({ ...f, score: s })),
    setFilterRating: (r: number) => setFilters(f => ({ ...f, rating: r })),
    showArchived,
    setShowArchived,
    refresh,
    recalculate,
    deleteLead,
    restoreLead,
    updateStatus,
    updateProduct,
    deleteBatch,
    startBlast,
    saveSalesAction,
    convertLead,
    createLead,
    updateLead,
  };
}