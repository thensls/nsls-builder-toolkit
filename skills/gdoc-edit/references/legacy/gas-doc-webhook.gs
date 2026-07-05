/**
 * gdoc-edit webhook — read, find/replace, insert-at-top, insert-after, append,
 * remove-matching paragraphs, and read comments on a Google Doc, in place.
 *
 * Deploy as a Web App:  Deploy → New deployment → Web app
 *   Execute as: Me        (runs as your Workspace identity — your Doc access)
 *   Who has access: Anyone (the shared secret below is what actually gates it)
 *
 * IMPORTANT: "Who has access" MUST be "Anyone". If it is "Anyone within <org>",
 * the /exec URL contains /a/macros/<domain>/ and an unauthenticated call gets a 401.
 *
 * Security: every request must include `token` matching the Script Property SHARED_SECRET.
 * Set it under  Project Settings (gear) → Script Properties → Add: SHARED_SECRET = <long random string>.
 *
 * After editing this code you MUST redeploy: Deploy → Manage deployments → ✏️ → Version: New version → Deploy.
 */

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const secret = PropertiesService.getScriptProperties().getProperty('SHARED_SECRET');
    if (!secret || body.token !== secret) {
      return json_({ ok: false, error: 'unauthorized' });
    }
    const docId = body.docId;
    switch (body.action) {
      case 'read':           return json_(readDoc_(docId));
      case 'replace':        return json_(replaceText_(docId, body.find, body.replace));
      case 'insertTop':      return json_(insertTop_(docId, body.title, body.text));
      case 'insertAfter':    return json_(insertAfter_(docId, body.anchor, body.title, body.text));
      case 'append':         return json_(appendText_(docId, body.text));
      case 'removeMatching': return json_(removeMatching_(docId, body.anchors));
      case 'comments':       return json_(listComments_(docId));
      default:               return json_({ ok: false, error: 'unknown action: ' + body.action });
    }
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

function readDoc_(docId) {
  const text = DocumentApp.openById(docId).getBody().getText();
  return { ok: true, length: text.length, text: text };
}

function replaceText_(docId, find, replace) {
  // `find` is a RE2 regular expression (Apps Script replaceText semantics).
  DocumentApp.openById(docId).getBody().replaceText(find, replace == null ? '' : replace);
  return { ok: true };
}

// Insert a changelog/section at the very top. `title` becomes a HEADING2; each line of `text`
// becomes a normal paragraph (use \n to separate lines).
function insertTop_(docId, title, text) {
  const docBody = DocumentApp.openById(docId).getBody();
  const lines = (text || '').split('\n');
  for (var i = lines.length - 1; i >= 0; i--) {
    docBody.insertParagraph(0, lines[i]).setHeading(DocumentApp.ParagraphHeading.NORMAL);
  }
  if (title) {
    docBody.insertParagraph(0, title).setHeading(DocumentApp.ParagraphHeading.HEADING2);
  }
  return { ok: true };
}

// Insert a section AFTER the first paragraph whose text contains `anchor`.
// `title` (optional) becomes a HEADING3; each line of `text` becomes a NORMAL paragraph.
// This is the clean way to add new bullets/sections mid-document (replaceText cannot
// create new paragraphs — \n in a replacement does not become a paragraph break).
function insertAfter_(docId, anchor, title, text) {
  const docBody = DocumentApp.openById(docId).getBody();
  const paras = docBody.getParagraphs();
  var idx = -1;
  for (var i = 0; i < paras.length; i++) {
    if (paras[i].getText().indexOf(anchor) !== -1) { idx = i; break; }
  }
  if (idx === -1) return { ok: false, error: 'anchor not found: ' + anchor };
  var insertAt = docBody.getChildIndex(paras[idx]) + 1;
  var items = [];
  if (title) items.push({ t: title, h: DocumentApp.ParagraphHeading.HEADING3 });
  (text || '').split('\n').forEach(function (ln) {
    items.push({ t: ln, h: DocumentApp.ParagraphHeading.NORMAL });
  });
  for (var k = 0; k < items.length; k++) {
    docBody.insertParagraph(insertAt + k, items[k].t).setHeading(items[k].h);
  }
  return { ok: true, insertedAfterIndex: idx };
}

function appendText_(docId, text) {
  DocumentApp.openById(docId).getBody().appendParagraph(text);
  return { ok: true };
}

// Remove WHOLE paragraphs whose text contains any of the given `anchors`.
// Use this to delete stale sections cleanly (replaceText with '' only empties text,
// leaving blank paragraphs behind). Anchors must be distinctive — anything matching is removed.
function removeMatching_(docId, anchors) {
  const docBody = DocumentApp.openById(docId).getBody();
  const paras = docBody.getParagraphs();
  var removed = 0;
  for (var i = paras.length - 1; i >= 0; i--) {
    var t = paras[i].getText();
    for (var j = 0; j < anchors.length; j++) {
      if (anchors[j] && t.indexOf(anchors[j]) !== -1) {
        try { docBody.removeChild(paras[i]); removed++; }
        catch (e) { paras[i].clear(); }   // body must keep >=1 child; clear if last
        break;
      }
    }
  }
  return { ok: true, removed: removed };
}

function listComments_(docId) {
  // Touch DriveApp once so authorization includes the Drive scope,
  // letting getOAuthToken() call the Drive REST comments endpoint.
  DriveApp.getFileById(docId).getName();
  const url = 'https://www.googleapis.com/drive/v3/files/' + docId +
    '/comments?fields=comments(id,author/displayName,content,quotedFileContent/value,resolved,' +
    'replies(author/displayName,content))&pageSize=100';
  const res = UrlFetchApp.fetch(url, {
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    muteHttpExceptions: true
  });
  return { ok: true, comments: (JSON.parse(res.getContentText()).comments || []) };
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
