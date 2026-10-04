# 16_REPORTING_AND_PDF_GUIDELINES

## 1. Overview

CERMS requires automated generation of official business documents, including Rental Quotations, Contracts, and Invoices as PDF files[cite: 1, 33]. This document defines the strict HTML and CSS standards required to generate pixel-perfect A4 documents using WeasyPrint[cite: 33].

## 2. PDF Generation Engine

- **Engine:** WeasyPrint is the designated library for converting HTML templates to PDFs[cite: 33]. ReportLab should only be used if dynamic drawing is strictly required.
- **Workflow:**
  1. Render a standard Django HTML template with context data.
  2. Pass the rendered HTML string to WeasyPrint.
  3. Return the generated PDF as an `HttpResponse` (for viewing/downloading) or save it to the database/S3.

## 3. A4 Page Layout & Print-Friendly CSS

AI must strictly adhere to print-specific CSS rules to ensure documents fit perfectly on standard A4 paper without overflowing.

```css
@page {
    size: A4;
    margin: 2cm;
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
        color: #666;
    }
}

body {
    font-family: 'Helvetica', 'Arial', sans-serif;
    font-size: 11pt; /* Use pt, cm, or mm. Do NOT use px, em, or rem for print */
    line-height: 1.5;
    color: #000;
}
4. UI/Layout Rules for PDF Templates
Avoid Modern Web Layouts: WeasyPrint has limited support for modern CSS Grid and complex Flexbox. Use standard <table> elements for data grids, invoice line items, and structured layouts.

Page Breaks: Prevent tables or important text blocks from splitting awkwardly across pages.

CSS
tr, .keep-together {
    page-break-inside: avoid;
}
h1, h2, h3, .invoice-header {
    page-break-after: avoid;
}
Static Assets in PDFs: Use absolute URIs for images (like company logos) so WeasyPrint can fetch them during generation. (e.g., passing request.build_absolute_uri() to the template context).

Colors and Backgrounds: Ensure high contrast. Use #000000 for primary text. Avoid large dark background areas that consume excessive printer ink.
```
