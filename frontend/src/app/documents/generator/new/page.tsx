"use client";
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
import { useDocumentGenerator } from "../../../../hooks/useDocumentGenerator";

export default function DocumentNewPage() {
  const ctx = useDocumentGenerator();

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <Breadcrumb items={[
        { label: "Document Generator", href: "/documents/generator" },
        { label: "Generate Baru" },
      ]} showBack backHref="/documents/generator" />
      <div>
        <h1 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">Generate Dokumen</h1>
        <p className="text-sm text-gray-500 mt-1">Buat PDF dari template dalam beberapa langkah.</p>
      </div>

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