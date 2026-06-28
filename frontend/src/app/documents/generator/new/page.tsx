"use client";
import { useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Toast from "../../../../components/Toast";
import Breadcrumb from "../../../../components/Breadcrumb";
import GeneratorSteps from "../../../../components/documents/GeneratorSteps";
import TemplatePicker from "../../../../components/documents/TemplatePicker";
import TargetPicker from "../../../../components/documents/TargetPicker";
import GeneratorForm from "../../../../components/documents/GeneratorForm";
import GeneratorPreview from "../../../../components/documents/GeneratorPreview";
import GeneratorSuccess from "../../../../components/documents/GeneratorSuccess";
import ProductPicker from "../../../../components/documents/ProductPicker";
import SequenceEditor from "../../../../components/documents/SequenceEditor";
import EmailModal from "../../../../components/documents/EmailModal";
import DraftSaveBar from "../../../../components/documents/DraftSaveBar";
import DraftLoader from "../../../../components/documents/DraftLoader";
import { useDocumentGenerator } from "../../../../hooks/useDocumentGenerator";

interface LineItem {
  id: string;
  name: string;
  description: string;
  qty: number;
  price: number;
}

function parseRupiah(value: string): number {
  const cleaned = value.replace(/[^0-9]/g, "");
  const parsed = parseInt(cleaned, 10);
  return isNaN(parsed) ? 0 : parsed;
}

function parseLineItemsFromHtml(html: string): LineItem[] {
  if (!html || !html.includes("<tr")) return [];
  const items: LineItem[] = [];
  const rowRegex = /<tr[^>]*>([\s\S]*?)<\/tr>/g;
  let match;
  while ((match = rowRegex.exec(html)) !== null) {
    const rowHtml = match[1];
    if (rowHtml.includes("<th") || rowHtml.includes("Total Tagihan") || rowHtml.includes("<tfoot")) continue;
    const nameMatch = rowHtml.match(/<strong[^>]*>([\s\S]*?)<\/strong>/);
    const descMatch = rowHtml.match(/<div[^>]*>([\s\S]*?)<\/div>/);
    const qtyMatch = rowHtml.match(/text-align:center[^>]*>(\d+)/);
    const priceMatches = Array.from(rowHtml.matchAll(/text-align:right[^>]*>([\s\S]*?)</g));
    if (nameMatch) {
      const name = nameMatch[1].trim();
      const description = descMatch ? descMatch[1].replace(/<[^>]*>/g, "").trim() : "";
      const qty = qtyMatch ? parseInt(qtyMatch[1], 10) : 1;
      const price = priceMatches.length >= 1 ? parseRupiah(priceMatches[0][1]) : 0;
      if (name) items.push({ id: `item-${items.length}`, name, description, qty, price });
    }
  }
  return items;
}

function DocumentNewPageInner() {
  const ctx = useDocumentGenerator();
  const searchParams = useSearchParams();
  const isEditMode = searchParams.get("edit") === "true";
  const editAppliedRef = useRef(false);

  // Detect edit mode: load variables from sessionStorage, find template, jump to step 2
  useEffect(() => {
    if (!isEditMode || editAppliedRef.current) return;
    const raw = sessionStorage.getItem("kt_edit_context");
    if (!raw) return;
    let editCtx: any;
    try { editCtx = JSON.parse(raw); } catch { return; }
    if (!editCtx.templateId) return;

    // Wait for templates to load
    const tmpl = ctx.templates.find(t => t.id === editCtx.templateId);
    if (!tmpl) return;

    // Apply edit context — directly set template and variables without
    // triggering selectTemplate's defaults fetch (which would overwrite edit values)
    editAppliedRef.current = true;
    ctx.setEditDocId(editCtx.docId || null);
    // Build template from stored variables so form renders the same fields as when saved
    const apiTmpl = ctx.templates.find(t => t.id === editCtx.templateId);
    ctx.setSelectedTemplate({
      id: editCtx.templateId,
      name: editCtx.templateName || apiTmpl?.name || "Template",
      type: apiTmpl?.type || "",
      variables: Object.keys(editCtx.variables || {}),
    });
    ctx.setVariables(editCtx.variables || {});
    // Load line items: try stored JSON first, fallback to parsing HTML from variables
    if (editCtx.line_items_json && Object.keys(editCtx.line_items_json).length > 0) {
      ctx.setLineItems(editCtx.line_items_json);
    } else {
      const items: Record<string, any[]> = {};
      const vars = editCtx.variables || {};
      for (const key of ["items_rows", "items_table", "line_items", "items"]) {
        if (vars[key] && typeof vars[key] === "string" && vars[key].includes("<tr")) {
          const parsed = parseLineItemsFromHtml(vars[key]);
          if (parsed.length > 0) items[key] = parsed;
        }
      }
      if (Object.keys(items).length > 0) ctx.setLineItems(items);
    }
    ctx.setStep(2); // Jump directly to form step
    sessionStorage.removeItem("kt_edit_context");
  }, [isEditMode, ctx.templates]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <Breadcrumb items={[
        { label: "Dokumen Resmi", href: "/documents/generator" },
        { label: isEditMode ? "Edit Dokumen" : "Buat Dokumen" },
      ]} showBack backHref="/documents/generator" />
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">
            {isEditMode ? "Edit Dokumen" : "Buat Dokumen Resmi"}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {isEditMode ? "Ubah variabel lalu regenerate PDF." : "Pilih template formal, target, lalu generate PDF."}
          </p>
        </div>
        <DraftSaveBar saving={ctx.draftSaving} lastSaved={ctx.lastSaved} hasDraft={ctx.step >= 1 && ctx.step <= 2 && !!ctx.selectedTemplate} />
      </div>

      {/* Draft Loader - hidden in edit mode */}
      {!isEditMode && (
        <DraftLoader
          drafts={ctx.drafts}
          loading={ctx.showDraftLoader && ctx.drafts.length === 0}
          onResume={ctx.loadDraft}
          onDelete={ctx.deleteDraft}
          onDismiss={() => ctx.setShowDraftLoader(false)}
        />
      )}

      <GeneratorSteps currentStep={ctx.step} />

      {/* Step 0: Pick Template */}
      {ctx.step === 0 && (
        <TemplatePicker
          templates={ctx.templates}
          selectedTemplate={ctx.selectedTemplate}
          selectTemplate={ctx.selectTemplate}
          setStep={ctx.setStep}
        />
      )}

      {/* Step 1: Pick Target */}
      {ctx.step === 1 && (
        <TargetPicker
          currentStep={ctx.step}
          setStep={ctx.setStep}
          selectedTemplate={ctx.selectedTemplate}
          targetType={ctx.targetType}
          setTargetType={ctx.setTargetType}
          leads={ctx.leads}
          contacts={ctx.contacts}
          projects={ctx.projects}
          filteredLeads={ctx.filteredLeads}
          filteredContacts={ctx.filteredContacts}
          filteredProjects={ctx.filteredProjects}
          targetSearch={ctx.targetSearch}
          setTargetSearch={ctx.setTargetSearch}
          selectedLead={ctx.selectedLead}
          selectedContact={ctx.selectedContact}
          selectedProject={ctx.selectedProject}
          pickLead={ctx.pickLead}
          pickContact={ctx.pickContact}
          pickProject={ctx.pickProject}
          fetchAndApplyDefaults={ctx.fetchAndApplyDefaults}
        />
      )}

      {/* Step 2: Fill Variables */}
      {ctx.step === 2 && (
        <GeneratorForm
          step={ctx.step}
          setStep={ctx.setStep}
          selectedTemplate={ctx.selectedTemplate}
          variables={ctx.variables}
          setVariables={ctx.setVariables}
          lineItems={ctx.lineItems}
          setLineItems={ctx.setLineItems}
          paymentMethods={ctx.paymentMethods}
          products={ctx.products}
          setProductPickerForKey={ctx.setProductPickerForKey}
          setProductPickerMode={ctx.setProductPickerMode}
          klienCandidates={ctx.klienCandidates}
          klienSearch={ctx.klienSearch}
          setKlienSearch={ctx.setKlienSearch}
          klienDropdownOpen={ctx.klienDropdownOpen}
          setKlienDropdownOpen={ctx.setKlienDropdownOpen}
          klienRef={ctx.klienRef}
          setShowSeqEditor={ctx.setShowSeqEditor}
          loadCurrentSequence={ctx.loadCurrentSequence}
          setToast={ctx.setToast}
          previewing={ctx.previewing}
          handlePreview={ctx.handlePreview}
        />
      )}

      {/* Step 3: Preview + Generate */}
      {ctx.step === 3 && (
        <GeneratorPreview
          selectedTemplate={ctx.selectedTemplate}
          selectedProject={ctx.selectedProject}
          selectedLead={ctx.selectedLead}
          selectedContact={ctx.selectedContact}
          previewUrl={ctx.previewUrl}
          previewing={ctx.previewing}
          handlePreview={ctx.handlePreview}
          generating={ctx.generating}
          handleGenerate={ctx.handleGenerate}
          setStep={ctx.setStep}
        />
      )}

      {/* Step 4: Done */}
      {ctx.step === 4 && (
        <GeneratorSuccess
          generatedDoc={ctx.generatedDoc}
          previewUrl={ctx.previewUrl}
          setPreviewUrl={ctx.setPreviewUrl}
          setStep={ctx.setStep}
          setSelectedTemplate={() => {}}
          setSelectedLead={() => {}}
          setSelectedContact={() => {}}
          setSelectedProject={() => {}}
          setVariables={ctx.setVariables}
          setLineItems={ctx.setLineItems}
          setGeneratedDoc={ctx.setGeneratedDoc}
          setTargetType={ctx.setTargetType}
          setTargetSearch={ctx.setTargetSearch}
          onNewDocument={() => ctx.setEmailModal(true)}
        />
      )}

      {/* Product Picker Modal */}
      <ProductPicker
        productPickerForKey={ctx.productPickerForKey}
        productPickerMode={ctx.productPickerMode}
        productSearch={ctx.productSearch}
        setProductSearch={ctx.setProductSearch}
        filteredProducts={ctx.filteredProducts}
        setProductPickerForKey={ctx.setProductPickerForKey}
        addLineItemFromProduct={ctx.addLineItemFromProduct}
        pickProductForSingleField={ctx.pickProductForSingleField}
      />

      {/* Sequence Editor Modal */}
      <SequenceEditor
        showSeqEditor={ctx.showSeqEditor}
        setShowSeqEditor={ctx.setShowSeqEditor}
        seqStartFrom={ctx.seqStartFrom}
        setSeqStartFrom={ctx.setSeqStartFrom}
        saveSequence={ctx.saveSequence}
      />

      {/* Email Modal */}
      <EmailModal
        emailModal={ctx.emailModal}
        setEmailModal={ctx.setEmailModal}
        emailTo={ctx.emailTo}
        setEmailTo={ctx.setEmailTo}
        emailSubject={ctx.emailSubject}
        setEmailSubject={ctx.setEmailSubject}
        sendingEmail={ctx.sendingEmail}
        handleSendEmail={ctx.handleSendEmail}
        generatedDoc={ctx.generatedDoc}
      />

      {ctx.toast && <Toast message={ctx.toast.message} type={ctx.toast.type} onClose={() => ctx.setToast(null)} />}
    </div>
  );
}

export default function DocumentNewPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-gray-400">Memuat...</div>}>
      <DocumentNewPageInner />
    </Suspense>
  );
}
