const routes = new Set(['image-led', 'layered', 'deterministic']);
const roles = new Set(['headline', 'support', 'fact', 'cta', 'detail']);
const treatments = new Set(['generated', 'original', 'editable', 'verified-image']);
const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
const hasText = (value) => typeof value === 'string' && value.trim() !== '';
const strings = (value) => Array.isArray(value) && value.every(hasText);
const count = (value) => Number.isSafeInteger(value) && value >= 0;

export function recommendProductionRoute(design) {
  if (design?.informationDensity === 'high') return 'deterministic';
  const exactLayers = Array.isArray(design?.layers) && design.layers.some((layer) =>
    layer?.treatment === 'original' || layer?.treatment === 'editable');
  return exactLayers ? 'layered' : 'image-led';
}

export function validateDesignAgreement(design, state, conceptRevision, approvedCopy = []) {
  if (!isObject(design)) return ['design must be an object'];
  const issues = [];
  const active = state !== 'intake' && state !== 'needs_rebrief';
  const composed = ['concept', 'visual_locked', 'publish', 'release'].includes(state);
  if (design.version !== 1) issues.push('design.version must be 1');
  for (const field of ['objective', 'audience', 'viewingContext', 'firstGlance', 'action']) {
    if (active ? !hasText(design[field]) : design[field] !== null && !hasText(design[field])) {
      issues.push(`design.${field} must describe the design agreement${active ? ' after intake' : ' or be null during intake'}`);
    }
  }
  if (!['low', 'medium', 'high'].includes(design.informationDensity)) issues.push('design.informationDensity must be low, medium, or high');
  if (!isObject(design.brand) || !strings(design.brand.preserve) || !strings(design.brand.avoid)) {
    issues.push('design.brand must contain preserve and avoid string arrays');
  }
  if (!Array.isArray(design.hierarchy) || (active && design.hierarchy.length === 0)) {
    issues.push('design.hierarchy must record information priority after intake');
  } else {
    const seen = new Set();
    for (const item of design.hierarchy) {
      if (!isObject(item) || !count(item.copyIndex) || item.copyIndex >= approvedCopy.length || seen.has(item.copyIndex)) {
        issues.push('design.hierarchy copyIndex must reference one unique approvedCopy entry');
      } else seen.add(item.copyIndex);
      if (!roles.has(item?.role) || !Number.isInteger(item?.priority) || item.priority < 1 || item.priority > 5) {
        issues.push('design.hierarchy entries need a content role and priority from 1 to 5');
      }
    }
  }
  if (!isObject(design.route) || (active ? !routes.has(design.route.kind) : design.route.kind !== null && !routes.has(design.route.kind))
      || (active && !hasText(design.route.reason))) {
    issues.push('design.route must record a production kind and reason after intake');
  }
  const exploration = design.exploration;
  if (!isObject(exploration) || !['direct', 'studies'].includes(exploration.approach)
      || !count(exploration.maxStudies) || !count(exploration.directionBudget)) {
    issues.push('design.exploration needs an approach and non-negative maxStudies/directionBudget');
  } else {
    if (exploration.approach === 'studies' && exploration.maxStudies < 2) issues.push('composition studies need maxStudies of at least 2');
    if (exploration.approach === 'direct' && exploration.maxStudies !== 0) issues.push('direct exploration uses maxStudies 0');
    if (conceptRevision > exploration.directionBudget) issues.push('conceptRevision exceeds the recorded directionBudget');
  }
  if (!Array.isArray(design.layers)) issues.push('design.layers must be an array');
  else {
    const seen = new Set();
    for (const layer of design.layers) {
      if (!isObject(layer) || !hasText(layer.id) || seen.has(layer.id) || !hasText(layer.role) || !treatments.has(layer.treatment)) {
        issues.push('design.layers need unique ids, roles, and generated/original/editable/verified-image treatment');
      } else seen.add(layer.id);
      if (composed && layer?.treatment === 'original' && !hasText(layer.source)) {
        issues.push('original design layers need an authorized source before concept delivery');
      }
    }
  }
  const approval = design.approval;
  if (!isObject(approval) || !['pending', 'confirmed'].includes(approval.status)
      || !strings(approval.locked) || !strings(approval.flexible)) {
    issues.push('design.approval needs status, locked, and flexible properties');
  } else {
    if (approval.locked.some((property) => approval.flexible.includes(property))) issues.push('design approval properties cannot be both locked and flexible');
    if (approval.status === 'confirmed' && (!hasText(approval.evidence) || approval.locked.length === 0)) {
      issues.push('confirmed design approval requires user evidence and locked properties');
    }
    if (['visual_locked', 'publish', 'release'].includes(state) && approval.status !== 'confirmed') {
      issues.push('design.approval must be confirmed before visual_locked, publish, or release');
    }
  }
  if (!strings(design.reviewContexts) || (active && design.reviewContexts.length === 0)) issues.push('design.reviewContexts must describe the actual viewing checks');
  if (!Array.isArray(design.deliverables) || (active && design.deliverables.length === 0)) {
    issues.push('design.deliverables must record the requested exports');
  } else {
    const ids = new Set();
    for (const item of design.deliverables) {
      if (!isObject(item) || !hasText(item.id) || ids.has(item.id) || !['png', 'pdf', 'source'].includes(item.format)
          || !hasText(item.usage) || !hasText(item.config)) {
        issues.push('design.deliverables need unique ids, format, usage, and a canvas config reference');
      } else ids.add(item.id);
    }
  }
  if (state === 'needs_rebrief' && !hasText(design.rebriefReason)) issues.push('needs_rebrief requires a specific design.rebriefReason');
  return issues;
}
