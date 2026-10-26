# Demo script

A 10-question walkthrough for the AI Boardroom demo. Each question exercises a different part
of the retrieval + grounding pipeline. Answers are grounded in the ingested
`abc-pharma-catalog` source and carry a dynamic citation.

Set the response style (Concise / Standard / Detailed / Executive) in the conversation header
to show adaptive formatting.

### 1. Portfolio overview
> What products are included in ABC Pharma's Product Catalog portfolio?

Demonstrates `PORTFOLIO_OVERVIEW` — structured retrieval of the whole catalogue.

### 2. Everything about a product
> Tell me everything available about DEMOCIN.

`EXACT_PRODUCT` — deterministic exact lookup, all available structured fields.

### 3. Composition lookup
> What is the composition of DEMOCIN?

`COMPOSITION_LOOKUP` — exact composition presented verbatim (no altered strengths/units).

### 4. Comparison
> Compare DEMOCIN and DEMOCIN O.

`PRODUCT_COMPARISON` — both products resolved exactly; the LLM only formats a comparison table
from evidence and does not discover data.

### 5. Ingredient search
> Which products contain Nurobalin?

`INGREDIENT_SEARCH` — deterministic ingredient / normalized-composition matching, not semantic
similarity.

### 6. Category search
> Show me all anti-infective products.

`CATEGORY_SEARCH` — category normalization + filter returns all matches.

### 7. Brand-family portfolio
> Tell me about the NUROBAL portfolio.

Brand-family exploration across related entries.

### 8. Semantic question
> Which products are associated with pain management?

`SEMANTIC_PRODUCT_SEARCH` / category — relationships described carefully, no implied clinical
equivalence.

### 9. Executive overview
> Give me an executive overview of the Product Catalog portfolio.

Set style to **Executive** — leadership-oriented summary with a takeaway line.

### 10. Grounded abstention
> What information do you have about products that isn't available in the source?

Demonstrates honesty: the assistant sticks to source-grounded information and does not invent
data that is not present.

## Also worth showing

- **Out of scope:** "What is ABC Pharma's market share?" -> declines, lists what it can help with.
- **Medical safety:** "What dose should I prescribe for my patient?" -> safety notice, no
  personalized prescribing advice.
- **Source filtering:** select a single source in the left rail and observe filtered retrieval
  and citations (scales to multiple sources).
- **Product Explorer** (`/products`): filter by source / category / ingredient; open a product
  detail page and use *Ask AI* / *Compare*.
