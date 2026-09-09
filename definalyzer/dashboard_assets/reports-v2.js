// Existing V2 reports remain readable. Normal creation uses the supported report workflow.
const experimentalReportsEnabled = false;
const renderOriginalReports = renderReports;
renderReports = function () {
  renderOriginalReports();
  document.querySelectorAll('#report-list .report-card').forEach((card, index) => {
    const report = state.reports[index];
    if (report.schema_version !== 2) return;
    const button = (action, label, primary = false) => `<button type="button" class="${primary ? 'primary' : ''}" data-report-action="${action}" data-report="${escapeText(report.report_id)}">${label}</button>`;
    const page = (path, label) => path ? `<button type="button" data-report-page="${escapeText(path)}">${label}</button>` : '';
    const recovery = experimentalReportsEnabled ? report.recovery : null;
    const actions = recovery ? [] : [page(report.report_page, 'Read report'), page(report.analyst_notes_page, 'Analyst notes')];
    actions.push(button('delete', 'Delete report'));
    if (recovery?.kind === 'prepare') actions.push(button('prepare', 'Prepare research', true));
    if (recovery?.kind === 'evidence') actions.push(button('sources', 'Add research sources', true));
    if (experimentalReportsEnabled && report.status === 'needs_attention' && reportActionAvailable(report, 'revise')) actions.push(button('repair', 'Fix review issues', true));
    for (const [key, action, label, primary] of [
      ['generate_draft', 'draft', report.status === 'needs_attention' ? 'Resume generation' : 'Generate report', true],
      ['revise', 'revise', 'Request a revision'], ['edit', 'edit', 'Edit wording'],
      ['reconcile', 'reconcile', 'Review my saved edits'], ['refresh_evidence', 'refresh', recovery?.kind === 'ready' ? 'Generate report' : 'Use latest research', recovery?.kind === 'ready'],
      ['finalize', 'finalize', 'Finalize', true], ['export', 'export', 'Export', true]
    ]) if (experimentalReportsEnabled && reportActionAvailable(report, key)) actions.push(button(action, label, primary));
    if (report.report_page && report.revision > 0) actions.push(button('history', 'Compare versions'));
    const labels = {scoped: 'Ready to generate', generating: 'Generating', needs_attention: 'Needs attention', ready_to_review: 'Ready for your review', final: 'Final'};
    card.innerHTML = `<div class="report-card-head"><div><h3>${escapeText(report.title)}</h3><p>${report.mode === 'full_review' ? 'Full review' : 'Answer a question'}</p></div><span class="report-status">${escapeText(recovery?.label || labels[report.status] || report.status)}</span></div>
      ${report.question ? `<p class="report-question">${escapeText(report.question)}</p>` : ''}
      <p>${escapeText(experimentalReportsEnabled ? (recovery?.message || report.message) : 'Saved experimental report. Reading and existing downloads remain available; create a new report for further research.')}</p>
      ${recovery?.missing_inputs?.length ? `<details ${recovery.kind === 'evidence' ? 'open' : ''}><summary>What is missing</summary><ul>${recovery.missing_inputs.map(reason => `<li>${escapeText(reason)}</li>`).join('')}</ul></details>` : ''}
      ${report.readiness === 'partial' ? '<p class="report-limit">A qualified answer: some conclusions still need more evidence. The report explains the limits.</p>' : ''}
      ${report.readiness === 'insufficient' && !recovery ? '<p class="report-limit">The saved evidence cannot answer this request yet. Analyst notes list the missing inputs.</p>' : ''}
      ${experimentalReportsEnabled && report.historical && !recovery ? '<p class="report-limit">Uses earlier research. This version and its sources are preserved; use latest research to create another version.</p>' : ''}
      <div class="report-actions">${actions.join('')}</div>
      ${(report.export_revisions || []).map(revision => `<div class="report-downloads"><span>Version ${revision + 1}</span>${[['Report.html','HTML'],['Report.pdf','PDF'],['Report.md','Markdown'],['Analyst-Notes.md','Analyst notes']].map(([file,label]) => `<a target="_blank" rel="noopener" href="${reportExportUrl(report,revision,file)}">${label}</a>`).join('')}</div>`).join('')}`;
  });
  bindReportPages();
  document.querySelectorAll('[data-report-action]').forEach(node => node.onclick = () => openReportAction(node.dataset.reportAction, node.dataset.report).catch(error => toast(error.message)));
};

function bindReportPages() {
  document.querySelectorAll('[data-report-page]').forEach(node => node.onclick = async () => {
    if ($('reports-dialog').open) $('reports-dialog').close();
    if ($('fact-dialog').open) $('fact-dialog').close();
    try { await openPage(node.dataset.reportPage); } catch (error) { toast(error.message); }
  });
}

if (experimentalReportsEnabled) newReportForm = function () {
  const unprepared = state.reports.find(report => report.schema_version === 2 && report.recovery?.kind === 'prepare');
  if (unprepared) return openReportAction('prepare', unprepared.report_id);
  openForm({title: 'New report', kicker: 'RESEARCH REPORT',
    fields: field('mode', 'What do you need?', 'select', '<option value="full_review">Full review</option><option value="question">Answer a question</option>') +
      field('question', 'Your research question', 'textarea') + field('title', 'Title (optional)') +
      '<details><summary>Writing preferences</summary>' + field('audience', 'Audience', 'select', '<option value="researcher">Researcher</option><option value="management">Management</option>') +
      field('depth', 'Length', 'select', '<option value="brief">Brief</option><option value="standard">Standard</option>') + check('recommendations', 'Include a recommendation if the evidence supports one') + '</details>' +
      '<p class="muted">The report uses saved source-supported research, checks its claims, and repairs issues automatically. It stops with clear missing inputs when the evidence cannot answer your request.</p>',
    submit: 'Generate report', handler: async values => {
      if (values.mode === 'question' && !values.question.trim()) throw new Error('Enter the question you want answered.');
      if (values.mode === 'full_review') values.question = '';
      const data = await api(`/api/projects/${encodeURIComponent(state.project.slug)}/reports`, {method: 'POST', body: JSON.stringify({...values, schema_version: 2})});
      state.reports.push(data.report);
      await startReportJob('draft', data.report.report_id);
    }});
  const toggle = () => { $('field-question').closest('.form-row').hidden = $('field-mode').value !== 'question'; };
  $('field-mode').onchange = toggle;
  toggle();
};
$('new-report').onclick = newReportForm;
if ($('reports-open')) $('reports-open').onclick = () => openReports().catch(error => toast(error.message));

const originalReportAction = openReportAction;
openReportAction = async function (action, reportId) {
  const report = state.reports.find(row => row.report_id === reportId);
  if (report?.schema_version !== 2) return originalReportAction(action, reportId);
  if (action === 'delete') return deleteReportForm(reportId);
  if (!experimentalReportsEnabled && action !== 'history') throw new Error('Existing V2 reports are read-only. Create a normal report from saved research.');
  const expected_revision = report.revision_hash;
  if (action === 'prepare' || action === 'sources') {
    $('reports-dialog').close();
    if (action === 'sources') return openTool('source');
    return openResearchPreparation();
  }
  if (action === 'repair') return startReportJob('revise', reportId, {expected_revision, instruction: 'Resolve the saved blocking review findings. Preserve the existing sections and paragraph identities. Change only paragraphs needing correction and any affected summary or conclusion.'});
  if (action === 'draft') return startReportJob('draft', reportId);
  if (action === 'reconcile') return startReportJob('reconcile', reportId, {expected_revision});
  if (action === 'refresh') return openForm({title: 'Use latest research', kicker: 'NEW VERSION',
    fields: '<p>Create a new version from the latest prepared research. Earlier versions and final exports stay saved. If the collected documentation has not been analyzed, prepare it through Analyze project first.</p>',
    submit: 'Generate new version', handler: () => startReportJob('refresh', reportId, {expected_revision})});
  if (action === 'finalize') return openForm({title: 'Finalize report', kicker: 'YOUR APPROVAL',
    fields: '<p>Save this exact reviewed report, analyst notes, and supporting sources as final. Later edits create another version.</p>' +
      check('human_approved', 'I have reviewed this report and approve this version') +
      (report.needs_recommendation_approval ? check('recommendation_approved', 'I also approve the included recommendation') : ''),
    submit: 'Finalize report', handler: values => {
      if (!values.human_approved) throw new Error('Approve the reviewed report to finalize it.');
      if (report.needs_recommendation_approval && !values.recommendation_approved) throw new Error('Approve the included recommendation to finalize it.');
      return startReportJob('finalize', reportId, {...values, expected_revision});
    }});
  const detail = await api(`/api/projects/${encodeURIComponent(state.project.slug)}/reports/${encodeURIComponent(reportId)}`);
  const revision = detail.report.revision_hash;
  if (action === 'history') {
    $('reports-dialog').close();
    $('fact-title').textContent = 'Compare versions';
    $('fact-content').innerHTML = `<p>Every saved version retains its original supporting sources.</p><div class="report-actions">${detail.revisions.map(row => `<button data-report-page="${escapeText(row.report_page)}">Read version ${row.revision + 1}</button>`).join('')}</div>` +
      (detail.revisions.length < 2 ? '<p>This is the first version.</p>' : detail.changes.map(change => `<section class="report-change"><h3>${change.support_changed ? 'Wording or supporting evidence changed' : 'Wording changed'}</h3><div class="report-comparison"><div><strong>Previous</strong><p>${escapeText(change.before || 'Added paragraph')}</p></div><div><strong>Current</strong><p>${escapeText(change.after || 'Removed paragraph')}</p></div></div></section>`).join('') || '<p>No narrative changes in this version.</p>');
    bindReportPages(); $('fact-dialog').showModal(); return;
  }
  if (action === 'revise') return openForm({title: 'Request a revision', kicker: 'NEW VERSION',
    fields: field('assertion_id', 'What should change?', 'select', '<option value="report">Whole report</option>' + detail.sections.map(section => `<optgroup label="${escapeText(section.title)}"><option value="${section.section_id}">Section: ${escapeText(section.title)}</option>${section.blocks.map((block,index) => `<option value="${block.block_id}">Paragraph ${index + 1}: ${escapeText(block.text.slice(0,100))}…</option>`).join('')}</optgroup>`).join('')) +
      field('instruction', 'Describe the change', 'textarea') + '<p class="muted">The revision keeps the same evidence and receives the same source checks. The summary and conclusion may change to stay consistent.</p>',
    submit: 'Create revised version', handler: values => startReportJob('revise', reportId, {...values, expected_revision: revision})});
  if (action === 'edit') return openForm({title: 'Edit report wording', kicker: 'NEW VERSION',
    fields: '<p>Your wording will be preserved and checked against the saved evidence before it can be finalized.</p>' + detail.sections.map(section => `<h3>${escapeText(section.title)}</h3>${section.blocks.map((block,index) => `<div class="form-row"><label for="edit-${block.block_id}">Paragraph ${index + 1}</label><textarea id="edit-${block.block_id}" name="${block.block_id}" rows="5">${escapeText(block.text)}</textarea></div>`).join('')}`).join(''),
    submit: 'Save and check edits', handler: texts => startReportJob('edit', reportId, {texts, expected_revision: revision})});
  if (action === 'export') return openForm({title: 'Export final report', kicker: 'SHAREABLE REPORT',
    fields: '<p>Create Markdown, standalone HTML, and PDF, with separate analyst notes.</p>' +
      (detail.suggested_charts.length ? '<p>Optional charts from dated, compatible documented quantities:</p>' + detail.suggested_charts.map((chart,index) => check('chart_' + index, escapeText(`${chart.title} · ${chart.unit} · ${chart.as_of}`))).join('') + '<p class="muted">These describe documented parameters for the stated period.</p>' : '<p class="muted">No compatible dated quantities are available for a chart.</p>'),
    submit: 'Create exports', handler: values => startReportJob('export', reportId, {markdown: true, html: true, pdf: true, chart_ids: detail.suggested_charts.filter((chart,index) => values['chart_' + index]).map(chart => chart.chart_id)})});
};

async function openResearchPreparation() {
  if (!experimentalReportsEnabled) throw new Error('Experimental V2 preparation is disabled. Use Analyze project.');
  const plan = await api(`/api/projects/${encodeURIComponent(state.project.slug)}/preparation`);
  if (!plan.sources.length) return openTool('source');
  const choices = plan.sources.map((source, i) => check(`source_${i}`, escapeText(source.title || source.path), source.recommended)).join('');
  return openForm({title: 'Prepare saved research',
    fields: '<p>Suggested documents are selected below. The job stops within 6 AI calls or 8 minutes, including checks and repairs. Completed work stays saved. You can stop it from Activity.</p>' + choices +
      '<p>Reports will show the scope of this selection. When preparation finishes, return to Reports to generate your answer.</p>',
    submit: 'Prepare selected documents', handler: values => {
      const source_paths = plan.sources.filter((_, i) => values[`source_${i}`]).map(source => source.path);
      if (!source_paths.length) throw new Error('Choose at least one saved document.');
      if (source_paths.length > 8) throw new Error('Choose at most eight documents for this preparation.');
      return startJob('prepare-research', {source_paths});
    }});
}

function bindReportSources(context) {
  if (!context) return;
  document.querySelectorAll('#markdown .report-citation a').forEach(link => link.onclick = async event => {
    event.preventDefault();
    const number = link.textContent.trim();
    const sid = 'S' + number;
    if (!context.source_ids.includes(sid)) return;
    try {
      const data = await api(`/api/projects/${encodeURIComponent(context.project)}/reports/${encodeURIComponent(context.report_id)}/sources/${context.revision}/${sid}`);
      const source = data.source;
      $('fact-title').textContent = 'Original report source';
      $('fact-content').innerHTML = `<h3>${escapeText(source.path)}</h3><p>Lines ${source.start_line}–${source.end_line} · saved with this report version</p><blockquote>${escapeText(source.quote)}</blockquote><h3>Surrounding passage</h3><pre style="white-space:pre-wrap">${escapeText(source.context)}</pre>`;
      $('fact-dialog').showModal();
    } catch (error) { toast(error.message); }
  });
}
