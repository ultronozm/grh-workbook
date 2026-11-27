;;; tex2html-local.el --- GRH workbook HTML postprocessing  -*- lexical-binding: t; -*-

;;; Commentary:

;; Site-specific additions to tex2html.el, loaded by it when present.
;; They run on `tex2html-postprocess-html-functions', after the generic
;; steps have resolved \ref, \eqref and section numbers from the aux files.
;;
;; - Theorem-like environments get their LaTeX numbers (Problem 2.1.3)
;;   instead of pandoc's running count (Problem 3).
;; - `thebibliography' entries get their labels and anchors back, and
;;   \cite renders as [Dav, Ch. 4] linking to them, instead of citeproc's
;;   "(Dav?, Ch. 4)".
;; - Accents on expanded macros (\bar\F) and nested aligned blocks
;;   are repaired for MathJax.
;; - Table-of-contents entries repeat the numbered heading text.
;; - Items with a stable tag in tags.tsv (scripts/make-tags.py) show it,
;;   small and grey, linking to tag/TAG.html.
;; - Problems carry stable IDs for the browser's progress tracker.

;;; Code:

(require 'cl-lib)
(require 'sgml-mode)
(require 'subr-x)
(require 'xml)

(defvar tex2html-theorem-names)
(defvar tex2html-index-export-options)
(declare-function label-number-hash-table "tex2html")
(declare-function tex2html-detex "tex2html")

(defun tex2html-local--div-end (beg)
  "Return the end of the element starting at BEG."
  (save-excursion
    (goto-char beg)
    (sgml-skip-tag-forward 1)
    (point)))

(defun tex2html-local--theorems (texfile)
  "Return the \\newtheorem environments of TEXFILE and their counters.
The value is a hash table mapping each environment to the counter it
is numbered with: itself, or COUNTER for \\newtheorem{ENV}[COUNTER]."
  (let ((map (make-hash-table :test 'equal)))
    (when (file-exists-p texfile)
      (with-temp-buffer
        (insert-file-contents texfile)
        (goto-char (point-min))
        (while (re-search-forward
                "^[ \t]*\\\\newtheorem{\\([^}]+\\)}\\(?:\\[\\([^]]+\\)\\]\\)?" nil t)
          (puthash (match-string 1) (or (match-string 2) (match-string 1))
                   map))))
    map))

(defun tex2html-local-fix-theorem-numbers (auxfile)
  "Number theorem-like divs as LaTeX does, using AUXFILE.
Labelled environments take their number from the aux file.  Unlabelled
ones continue the count of their counter within the current section, as
for \\newtheorem{problem}{Problem}[section].  Environments declared
with \\newtheorem in the note are handled too, and those declared as
\\newtheorem{ENV}[COUNTER] share COUNTER."
  (let* ((labels (label-number-hash-table auxfile))
         (theorems (tex2html-local--theorems
                    (concat (file-name-sans-extension auxfile) ".tex")))
         (counters (make-hash-table :test 'equal))
         (env-re (regexp-opt (append tex2html-theorem-names
                                     (hash-table-keys theorems))))
         prefix)
    (goto-char (point-min))
    (while (re-search-forward
            (concat "<h1\\([^>]*\\)>\\|<div\\(?: id=\"\\([^\"]+\\)\"\\)? class=\"\\("
                    env-re "\\)\">")
            nil t)
      (if (match-beginning 1)
          (let ((attrs (match-string 1)))
            (unless (string-match-p "unnumbered" attrs)
              (clrhash counters)
              (setq prefix
                    (and (string-match "id=\"\\([^\"]+\\)\"" attrs)
                         (gethash (match-string 1 attrs) labels)))))
        (let* ((label (match-string 2))
               (env (gethash (match-string 3) theorems (match-string 3)))
               (end (tex2html-local--div-end (match-beginning 0)))
               (number (and label (gethash label labels))))
          (if number
              (when (string-match "\\([0-9]+\\)\\'" number)
                (puthash env (string-to-number (match-string 1 number))
                         counters))
            (let ((n (1+ (gethash env counters 0))))
              (puthash env n counters)
              (setq number (if prefix (format "%s.%d" prefix n)
                             (number-to-string n)))))
          (when (re-search-forward
                 "<strong>\\([^<]*?\\) [0-9.]+</strong>" end t)
            (replace-match (concat "<strong>\\1 " number "</strong>")
                           t nil)))))))

(defun tex2html-local--bibitems (texfile)
  "Return the \\bibitem entries of TEXFILE as (KEY LABEL BODY) lists.
BODY is the TeX source of the entry."
  (when (file-exists-p texfile)
    (with-temp-buffer
      (insert-file-contents texfile)
      (goto-char (point-min))
      (let ((bib-end (save-excursion
                       (and (re-search-forward "\\\\end{thebibliography}" nil t)
                            (match-beginning 0))))
            (item-re "\\\\bibitem\\(?:\\[\\([^]]*\\)\\]\\)?{\\([^}]+\\)}")
            items (n 0))
        (while (and bib-end (re-search-forward item-re bib-end t))
          (setq n (1+ n))
          (let* ((key (string-trim (match-string 2)))
                 (label (or (match-string 1) (number-to-string n)))
                 (body-beg (match-end 0))
                 (body-end (save-excursion
                             (if (re-search-forward item-re bib-end t)
                                 (match-beginning 0)
                               bib-end))))
            (push (list key (tex2html-detex label)
                        (string-trim (buffer-substring-no-properties
                                      body-beg body-end)))
                  items)))
        (nreverse items)))))

(defun tex2html-local--latex-to-html (tex)
  "Convert the LaTeX fragment TEX to HTML with pandoc."
  (with-temp-buffer
    (insert tex)
    (if (eq 0 (call-process-region (point-min) (point-max) "pandoc" t '(t nil) nil
                                   "-f" "latex" "-t" "html" "--wrap=none"
                                   "--mathjax"))
        (string-trim (buffer-string))
      (message "Warning: pandoc failed on bibliography entry: %s" tex)
      (xml-escape-string (tex2html-detex tex)))))

(defun tex2html-local--entry-html (body)
  "Return the HTML of a bibliography entry BODY, without paragraph tags."
  (let ((html (tex2html-local--latex-to-html body)))
    (if (string-match "\\`<p>\\(\\(?:.\\|\n\\)*\\)</p>\\'" html)
        (match-string 1 html)
      html)))

(defun tex2html-local-fix-bibliography (auxfile)
  "Rebuild the bibliography of AUXFILE's note and render its citations.
Pandoc drops \\bibitem labels and merges entries not separated by
blank lines, so the list is rebuilt from the TeX source with anchors
ref-KEY, and citations become [Label, note] links to them."
  (let* ((texfile (concat (file-name-sans-extension auxfile) ".tex"))
         (items (tex2html-local--bibitems texfile)))
    (when items
      (goto-char (point-min))
      (when (re-search-forward "<div class=\"thebibliography\">" nil t)
        (let ((beg (match-beginning 0))
              (end (tex2html-local--div-end (match-beginning 0))))
          (delete-region beg end)
          (goto-char beg)
          (insert "<h1 class=\"unnumbered\" id=\"references\">References</h1>\n"
                  "<div class=\"thebibliography\">\n")
          (dolist (item items)
            (insert (format "<p id=\"ref-%s\"><span class=\"bib-label\">[%s]</span> %s</p>\n"
                            (nth 0 item) (nth 1 item)
                            (tex2html-local--entry-html (nth 2 item)))))
          (insert "</div>")))
      ;; Citations: (<strong>Key?</strong>, note) -> [Label, note].
      (goto-char (point-min))
      (while (re-search-forward "<span[[:space:]]+class=\"citation\"[[:space:]]+data-cites=\"[^\"]*\">" nil t)
        (let* ((beg (match-beginning 0))
               (content-beg (match-end 0))
               (end (copy-marker (tex2html-local--div-end beg)))
               (content-end (- end (length "</span>"))))
          (goto-char content-beg)
          (when (and (eq (char-after content-beg) ?\()
                     (eq (char-before content-end) ?\)))
            (save-excursion
              (goto-char (1- content-end))
              (delete-char 1)
              (insert "]"))
            (delete-char 1)
            (insert "["))
          (while (re-search-forward "<strong>\\([^<]+\\)\\?</strong>" end t)
            (let* ((key (match-string 1))
                   (label (nth 1 (assoc key items))))
              (when label
                (replace-match (format "<a href=\"#ref-%s\">%s</a>" key label)
                               t t))))
          (goto-char end)
          (set-marker end nil))))))

(defun tex2html-local-fix-math (_auxfile)
  "Repair two kinds of math that MathJax rejects.
Pandoc expands macros in place, so \\bar\\F becomes \\bar\\mathbb{F},
in which \\bar takes \\mathbb as its argument; brace such arguments.  The
generic step that turns pandoc's aligned back into align also hits a
genuine aligned nested in another display environment; restore those."
  (goto-char (point-min))
  (while (re-search-forward
          (concat "\\\\\\(bar\\|hat\\|tilde\\|widetilde\\|widehat\\|overline"
                  "\\|underline\\|vec\\|dot\\|ddot\\|check\\|breve\\)"
                  "[ \t]*\\(\\\\\\(?:math[a-z]+\\|operatorname\\|boldsymbol\\)"
                  "{[^{}]*}\\)")
          nil t)
    (replace-match "\\\\\\1{\\2}" t nil))
  (goto-char (point-min))
  (while (re-search-forward "\\\\begin{align}" nil t)
    (unless (save-excursion
              (goto-char (match-beginning 0))
              (skip-chars-backward " \t\n")
              (looking-back "\\\\\\[" (- (point) 2)))
      (replace-match "\\\\begin{aligned}" t nil)
      (when (re-search-forward "\\\\end{align}" nil t)
        (replace-match "\\\\end{aligned}" t nil)))))

(defun tex2html-local-fix-toc (_auxfile)
  "Make table-of-contents entries repeat their headings' text."
  (goto-char (point-min))
  (while (re-search-forward
          "<a href=\"#\\([^\"]+\\)\"[ \n]+id=\"toc-[^\"]*\">\\(\\(?:.\\|\n\\)*?\\)</a>" nil t)
    (let* ((id (match-string 1))
           (text-beg (match-beginning 2))
           (text-end (match-end 2))
           (heading
            (save-excursion
              (goto-char (point-min))
              (when (re-search-forward
                     (format "<h[1-6][^>]* id=\"%s\"[^>]*>\\(\\(?:.\\|\n\\)*?\\)</h[1-6]>"
                             (regexp-quote id))
                     nil t)
                (match-string 1)))))
      (when heading
        (let ((text (string-trim
                     (replace-regexp-in-string
                      "[ \n]+" " "
                      (replace-regexp-in-string "<[^>]*>" "" heading)))))
          (delete-region text-beg text-end)
          (goto-char text-beg)
          (insert text))))))

(defun tex2html-local--tags (sheet &optional retired)
  "Return the live tags of SHEET in tags.tsv as (TAG . LABEL) pairs.
SHEET is a Denote timestamp; LABEL is \"\" for the chapter itself.
With RETIRED non-nil, return only the retired tags instead."
  (when (file-exists-p "tags.tsv")
    (with-temp-buffer
      (insert-file-contents "tags.tsv")
      (let (tags)
        (dolist (line (split-string (buffer-string) "\n" t))
          (unless (string-prefix-p "#" line)
            (let ((cols (split-string line "\t")))
              (when (and (equal (string-trim (or (nth 1 cols) "")) sheet)
                         (eq (not retired)
                             (string-empty-p (string-trim (or (nth 3 cols) "")))))
                (push (cons (string-trim (nth 0 cols))
                            (string-trim (or (nth 2 cols) "")))
                      tags)))))
        (nreverse tags)))))

(defun tex2html-local-add-tags (auxfile)
  "Show the stable tags of AUXFILE's sheet beside their items.
The chapter's tag goes in the title, a section's in its heading, and a
result's at the top of its box, each as a link to tag/TAG.html."
  (let ((sheet (substring (file-name-nondirectory auxfile) 0
                          (min 15 (length (file-name-nondirectory auxfile))))))
    (dolist (tag (tex2html-local--tags sheet))
      (let ((link (format (concat "<a class=\"stable-tag\" href=\"tag/%s.html\""
                                  " title=\"Stable tag: cite as Tag %s\">Tag %s</a>")
                          (car tag) (car tag) (car tag))))
        (goto-char (point-min))
        (cond
         ((string-empty-p (cdr tag))
          (when (re-search-forward "<h1 class=\"title\"[^>]*>" nil t)
            (when (search-forward "</h1>" nil t)
              (goto-char (match-beginning 0))
              (insert " " link))))
         ((re-search-forward
           (format "<\\(h[1-6]\\|div\\)\\b[^>]* id=\"%s\"[^>]*>"
                   (regexp-quote (cdr tag)))
           nil t)
          (if (equal (match-string 1) "div")
              (insert link)
            (when (search-forward (format "</%s>" (match-string 1)) nil t)
              (goto-char (match-beginning 0))
              (insert " " link))))
         (t (message "Warning: no element for tag %s (%s)"
                     (car tag) (cdr tag))))))))

(defun tex2html-local-add-progress (auxfile)
  "Emit progress IDs for the problems in AUXFILE's sheet.
A tagged problem uses its tag, with the file-and-label ID accepted
as an alias for marks made before the tag was assigned.  Reused
labels with retired tags do not get an alias."
  (let* ((texfile (concat (file-name-base auxfile) ".tex"))
         (sheet (substring texfile 0 (min 15 (length texfile))))
         (tags (tex2html-local--tags sheet))
         (retired (tex2html-local--tags sheet t))
         (seen (make-hash-table :test 'equal)))
    (goto-char (point-min))
    (while (re-search-forward
            "<div\\(?: id=\"\\([^\"]+\\)\"\\)? class=\"problem\">" nil t)
      (if-let* ((anchor (match-string 1))
                (label (xml-substitute-special anchor)))
          (let* ((fallback (concat texfile "#" label))
                 (tag (car (rassoc label tags)))
                 (ids (cond
                       ((not tag) (vector fallback))
                       ((rassoc label retired) (vector tag))
                       (t (vector tag fallback)))))
            (when (gethash (aref ids 0) seen)
              (error "Duplicate progress ID %s in %s" (aref ids 0) texfile))
            (puthash (aref ids 0) t seen)
            (backward-char)
            (insert " data-progress-ids=\"" (xml-escape-string (json-encode ids)) "\""))
        (message "Warning: a problem in %s needs a LaTeX label for progress tracking"
                 texfile)))
    (unless (zerop (hash-table-count seen))
      (goto-char (point-min))
      (search-forward "</head>")
      (goto-char (match-beginning 0))
      (insert "<link rel=\"stylesheet\" href=\"progress.css\">\n"
              "<script src=\"progress.js\" defer></script>\n"))))

(defun tex2html-local-add-reference-previews (auxfile)
  "Add reference preview assets and the chapter number for AUXFILE."
  (when-let* ((number (gethash "chap" (label-number-hash-table auxfile))))
    (goto-char (point-min))
    (search-forward "</head>")
    (goto-char (match-beginning 0))
    (insert "<meta name=\"workbook-chapter\" content=\""
            (xml-escape-string number) "\">\n"
            "<link rel=\"stylesheet\" href=\"reference-preview.css\">\n"
            "<script src=\"reference-preview.js\" defer></script>\n")))

(defun tex2html-local-index-progress (item _backend _info)
  "Attach the built sheet's problem IDs and destinations to the first sheet link in Org ITEM."
  (when (string-match
         (concat "\\`\\(?:<li>[[:space:]]*\\)?\\(?:<p>[[:space:]]*\\)?"
                 "<a href=\"\\([0-9]\\{8\\}T[0-9]\\{6\\}--[^/\"<>]+__workbook\\.html\\)\"")
         item)
    (let ((page (match-string 1 item))
          (link-end (match-end 0))
          ids destinations)
      (when (and (not (string-prefix-p " data-sheet-progress=" (substring item link-end)))
                 (file-readable-p page))
        (with-temp-buffer
          (insert-file-contents page)
          (goto-char (point-min))
          ;; These values are already JSON-encoded and escaped for HTML.
          (while (re-search-forward
                  (concat "<div id=\"\\([^\"]+\\)\" class=\"problem\""
                          " data-progress-ids=\"\\([^\"]+\\)\">[[:space:]]*"
                          "\\(?:<a class=\"stable-tag\"[^>]*>[^<]*</a>[[:space:]]*\\)?"
                          "<p><strong>\\(Problem [^<]+\\)</strong>")
                  nil t)
            (let ((anchor (match-string 1))
                  (label (match-string 3)))
              (push (match-string 2) ids)
              (push (vector (xml-substitute-special anchor) label) destinations)))))
      (when ids
        (concat (substring item 0 link-end)
                " data-sheet-progress=\"[" (mapconcat #'identity (nreverse ids) ",") "]\""
                " data-sheet-problems=\""
                (xml-escape-string (json-encode (vconcat (nreverse destinations))))
                "\""
                (substring item link-end))))))

(setq tex2html-index-export-options
      (plist-put tex2html-index-export-options :filter-item
                 '(tex2html-local-index-progress)))
(setq tex2html-index-export-options
      (plist-put tex2html-index-export-options :filter-paragraph
                 '(tex2html-local-index-progress)))

(add-hook 'tex2html-postprocess-html-functions #'tex2html-local-fix-theorem-numbers)
(add-hook 'tex2html-postprocess-html-functions #'tex2html-local-fix-bibliography t)
(add-hook 'tex2html-postprocess-html-functions #'tex2html-local-fix-math t)
(add-hook 'tex2html-postprocess-html-functions #'tex2html-local-fix-toc t)
;; After the table of contents, which copies the headings' text.
(add-hook 'tex2html-postprocess-html-functions #'tex2html-local-add-tags t)
(add-hook 'tex2html-postprocess-html-functions #'tex2html-local-add-progress t)
(add-hook 'tex2html-postprocess-html-functions #'tex2html-local-add-reference-previews t)

(provide 'tex2html-local)
;;; tex2html-local.el ends here
