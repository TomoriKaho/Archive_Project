export const INDENT_STEP = 14;

export function isObjectLike(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export function isDisplayEmptyString(value) {
  return typeof value === 'string' && value.trim() === '';
}

export function formatPrimitive(value) {
  if (value === undefined) return '';
  if (value === null) return 'null';
  return String(value);
}

export function parseStructuredValue(value) {
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch (error) {
      return value;
    }
  }
  return value;
}

export function buildBlocksFromValue(value, depth = 0) {
  if (isObjectLike(value)) {
    return Object.entries(value)
      .filter(([, entryValue]) => !isDisplayEmptyString(entryValue))
      .map(([key, entryValue]) => {
        const isChildStructured = isObjectLike(entryValue) || Array.isArray(entryValue);
        const childBlocks = isChildStructured ? buildBlocksFromValue(entryValue, depth + 1) : undefined;
        const valueText = isChildStructured ? undefined : formatPrimitive(entryValue);
        const hasChildren = Array.isArray(childBlocks) && childBlocks.length > 0;
        const hasValue = valueText !== undefined && valueText !== '';

        if (!hasChildren && !hasValue) {
          return null;
        }

        return {
          label: key,
          valueText: hasValue ? valueText : undefined,
          children: hasChildren ? childBlocks : undefined,
          depth
        };
      })
      .filter(Boolean);
  }

  if (Array.isArray(value)) {
    return value.map((item, index) => {
      const isChildStructured = isObjectLike(item) || Array.isArray(item);
      const childBlocks = isChildStructured ? buildBlocksFromValue(item, depth + 1) : undefined;
      const valueText = isChildStructured ? undefined : formatPrimitive(item);

      return {
        label: `[${index}]`,
        valueText,
        children: isChildStructured ? childBlocks : undefined,
        depth,
        index
      };
    });
  }

  return [
    {
      label: '',
      valueText: formatPrimitive(value),
      children: undefined,
      depth
    }
  ];
}

export function toCleanText(value) {
  if (value === null || value === undefined) return '';
  const text = typeof value === 'string' ? value.trim() : String(value);
  return text.trim();
}

export function normalizeArchiveNode(item) {
  if (!item || typeof item !== 'object') return null;
  const unitid = toCleanText(item.unitid);
  const title = toCleanText(item.title);
  const date = toCleanText(item.date);
  const extent = toCleanText(item.extent);
  const scopecontent = toCleanText(item.scopecontent);

  const children = Array.isArray(item.children)
    ? item.children.map((child) => normalizeArchiveNode(child)).filter(Boolean)
    : [];

  if (!unitid && !title && !date && !extent && !scopecontent && !children.length) {
    return null;
  }

  return {
    unitid,
    title,
    date,
    extent,
    scopecontent,
    children
  };
}

export function normalizeArchiveNodes(value) {
  if (!value) return [];
  const list = Array.isArray(value) ? value : [value];
  return list.map((item) => normalizeArchiveNode(item)).filter(Boolean);
}

export function hasArchiveText(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string') return value.trim() !== '';
  return String(value).trim() !== '';
}

export function isArchiveTreeNodeLike(node) {
  if (!isObjectLike(node)) return false;
  const hasMetadata = ['unitid', 'title', 'date', 'extent', 'scopecontent'].some((key) =>
    hasArchiveText(node[key])
  );
  const children = Array.isArray(node.children) ? node.children : [];
  const hasChildNode = children.some((child) => isArchiveTreeNodeLike(child));
  return hasMetadata || hasChildNode;
}

export function isArchiveTreeValue(rawValue) {
  const parsed = parseStructuredValue(rawValue);
  if (!parsed) return false;
  const values = Array.isArray(parsed) ? parsed : [parsed];
  return values.some((value) => isArchiveTreeNodeLike(value));
}

export function isStructuredRenderable(value) {
  const parsed = parseStructuredValue(value);
  return isObjectLike(parsed) || Array.isArray(parsed);
}

export function formatStructuredFallback(value, emptyPlaceholder = '—') {
  if (value === null || value === undefined) return emptyPlaceholder;
  if (typeof value === 'string') return value || emptyPlaceholder;
  try {
    return JSON.stringify(value, null, 2);
  } catch (error) {
    return String(value);
  }
}
