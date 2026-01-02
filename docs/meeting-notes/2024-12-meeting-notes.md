# Grana Platform - Meeting Notes December 2024

## Meeting Date: Late December 2024

### Attendees
- Macarena (Grana)
- Team (TM3)
- Vicente & Sebastián (Practice engineers from UCED)

---

## Summary

### New Team Members
- Vicente and Sebastián joined the team as practice engineers (Civil Engineering in Computing from UCED)
- They will be involved in future development including camera integration

### Data Precision Issues Identified
- Macarena identified inconsistencies in sales prices when analyzing the income statement manually
- Some products show highly variable average prices between months (e.g., granola sold at $5,800 some months and $3,800 in others) - this doesn't reflect reality
- **Main problem**: How to account for packs (like Pack Navidad) where individual item pricing is unclear
- **Solution discussed**: Take the price data from RelBase, which details the unit price in each invoice

### Dashboard Improvements Implemented
- Added consolidated filter control at the top with options:
  - Year to Date
  - Current month
  - Previous month
  - Last 12 months
  - Custom range
- Filter control stays fixed when scrolling and synchronizes all charts on the page
- Simplified the view to avoid fragmentation and enable quick sales pattern analysis

### Inventory and Planning Features
- Created a new "Planning" view separate from general inventory
- System allows selecting different sales patterns to calculate trends (last month, last 6 months, etc.)
- Automatically calculates stock coverage in days and recommended minimum stock
- Platform will identify products with excess stock to suggest offers before expiration
- Current inventory shows healthy stock without excess or shortages

### SKU and Catalog Management
- Reviewed all SKU mappings (400+)
- ANU and legacy codes are mapped but saturate the views
- **Decision**: Apply the same recategorization logic used in warehouse to sales, showing only catalog products
- **Bug found**: Granola conversions were wrong (10 units instead of 20), affecting calculations

### Excel Export Functionality
- Implemented export of grouped reports from the order breakdown table
- Allows grouping by month and filtering by product family
- **Missing**: Date column when grouping by month (requested for clarity)
- **Request**: Add this export functionality to the visualizations view as well

### Caja Master Counting Issue
- **Problem identified**: Master boxes (cajas master) are not automatically counted with their corresponding products
- This forced manual selection of each format, causing counting errors
- **Decision**: Master boxes should be counted automatically within the primary SKU product

### Data Integrations Status

| Source | Status | Notes |
|--------|--------|-------|
| RelBase | Primary source | Has inconsistencies, "has a life of its own" according to Macarena |
| Mercado Libre | Integrated directly | Missing expiration date |
| Amplifica | Was manual from RelBase | - |
| KeyLog | Pending | Will be main warehouse, review documentation with Osvaldo |
| Pac-Man | No API | Will be removed from RelBase along with Macarena's personal warehouse |

### Other Requested Improvements
- Change dashboard number visualization from abbreviated format (M, K) to complete numbers
- Added user profile section with role management and password reset
- Roles will be important when implementing the production module (access restrictions needed)

---

## Action Items

### TM3 Team
- [ ] Complete all mentioned changes by Friday, December 27, 2024
- [ ] Implement legacy code (ANU) recategorization in sales, showing only catalog items
- [ ] Fix automatic master box counting within primary SKU products
- [ ] Add Excel export functionality to visualizations view
- [ ] Change dashboard numbers to complete format (not abbreviated)
- [ ] Add date column in grouped Excel exports
- [ ] Coordinate with Osvaldo from KeyLog for API integration
- [ ] Send quote for Phase 2.0 in January 2026

### Macarena
- [ ] Update RelBase inventory, removing Pac-Man and personal warehouse (between today and tomorrow)

---

## Next Steps
- Macarena will travel from January 2-9 (Rio de Janeiro)
- Team is closing 2025 with multiple projects
- Need real inventory data to test the planning module
- First phase is very close to completion
- Phase 2.0 quote to be sent in January 2026

---

## Technical Notes

### Master Box Counting Logic (Key Decision)
When viewing a product format like "BARRA LOW CARB BERRIES X5" (BABE_U20010):
- Must include both:
  - Direct sales of BABE_U20010 (x5 packs)
  - Sales of BABE_C02810 (master box containing 28 x BABE_U20010)
- Conversion: 1 master box = 28 × 5 = 140 individual bars
- Uses `sku_master` relationship from `product_catalog` table
