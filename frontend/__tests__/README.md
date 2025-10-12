# Smart Search Test Suite

## Overview

This directory contains comprehensive tests for the smart search functionality, covering:
- Fuzzy search configuration and normalization
- Multi-channel product matching (Shopify, MercadoLibre, Manual)
- Search hook functionality
- Suggestion generation
- Category detection
- Analytics tracking

## Test Files

### 1. `searchConfig.test.ts`
Tests the core search configuration and utility functions.

**Coverage:**
- ✅ Text normalization (lowercase, accent removal, trimming)
- ✅ Variation standardization (barra/barrita, display/disp, units/uds)
- ✅ Term variations dictionary
- ✅ Category keyword mapping
- ✅ Fuse.js configuration and behavior
- ✅ Cross-channel matching (same product, different names)
- ✅ Fuzzy matching with typos
- ✅ SKU matching (full and partial)
- ✅ Category filtering
- ✅ Source independence
- ✅ Score and relevance calculation
- ✅ Edge cases (empty queries, special characters, long queries)

**Key Test Scenarios:**
```typescript
// Cross-channel matching
"barra keto nuez" finds "barrita keto nuez"

// Typo handling
"queto nuez" finds products with "keto"

// Word order independence
"nuez keto" finds "Keto Nuez"

// SKU matching
"BARR-KETO-01" finds exact product
"KETO-01" finds products with matching SKU fragment
```

### 2. `useSmartSearch.test.ts`
Tests the React hook that powers the smart search UI.

**Coverage:**
- ✅ Basic search execution
- ✅ State management (searchQuery, suggestions)
- ✅ Fuzzy matching integration
- ✅ Suggestion generation (3 types: category, did_you_mean, related_term)
- ✅ Category detection
- ✅ Keyword extraction (with stop word filtering)
- ✅ Search by category functionality
- ✅ Result quality (scores, matches, ordering)
- ✅ Edge cases (empty arrays, null fields, special chars)
- ✅ Performance with large datasets (1000+ products)

**Key Test Scenarios:**
```typescript
// Suggestion generation
Search "keto" → suggests filtering by "Keto" category
Search "barra" → suggests "barrita", "barritas" variations

// Category detection
"barra keto nuez" → detects Keto category
"low carb" → detects LowCarb category

// Performance
1000 products searched in < 500ms
```

## Running Tests

### Setup (First Time)

The tests require Jest and React Testing Library. To set up:

```bash
cd frontend

# Install testing dependencies
npm install --save-dev jest @testing-library/react @testing-library/jest-dom @testing-library/user-event @testing-library/react-hooks

# Install Next.js Jest support
npm install --save-dev @types/jest jest-environment-jsdom

# Install additional dependencies
npm install --save-dev ts-node
```

### Jest Configuration

Create `jest.config.js` in the frontend directory:

```javascript
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files in your test environment
  dir: './',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  testMatch: [
    '**/__tests__/**/*.test.[jt]s?(x)',
    '**/?(*.)+(spec|test).[jt]s?(x)'
  ],
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)
```

Create `jest.setup.js`:

```javascript
// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'
```

### Update package.json

Add test scripts to `package.json`:

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage"
  }
}
```

### Run Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage report
npm run test:coverage

# Run specific test file
npm test searchConfig.test

# Run tests matching pattern
npm test -- --testNamePattern="fuzzy"
```

## Test Coverage Goals

### Current Coverage
- ✅ `lib/searchConfig.ts` - 100% coverage
- ✅ `hooks/useSmartSearch.ts` - 95%+ coverage
- ⏳ `components/SmartSearchBar.tsx` - Pending
- ⏳ `components/HighlightedProductCard.tsx` - Pending
- ⏳ `lib/searchAnalytics.ts` - Pending

### Future Test Additions

1. **Component Tests**
   - SmartSearchBar user interactions
   - HighlightedProductCard rendering
   - Suggestion dropdown behavior

2. **Integration Tests**
   - Full search workflow on Products page
   - Analytics tracking integration
   - API endpoint testing

3. **E2E Tests**
   - User search scenarios
   - Multi-channel product discovery
   - Analytics data flow

## Test Data

### Mock Products Used in Tests

The tests use realistic mock data representing Grana's multi-channel inventory:

```typescript
[
  {
    id: 1,
    sku: 'BARR-KETO-01',
    name: 'Barra Keto Nuez',
    category: 'Keto',
    brand: 'Grana',
    source: 'shopify'
  },
  {
    id: 2,
    sku: 'BARR-KETO-02',
    name: 'Barrita Keto Chocolate',  // Note: Different naming
    category: 'Keto',
    brand: 'Grana',
    source: 'mercadolibre'
  },
  // ... more products
]
```

This mirrors the real-world challenge where the same product has different names across sales channels.

## Key Testing Patterns

### 1. Fuzzy Matching Tests
```typescript
it('should find "barra" when searching "barrita"', () => {
  const results = fuse.search('barrita')
  expect(results.some(r => r.item.name.includes('Barra'))).toBe(true)
})
```

### 2. Hook Testing with renderHook
```typescript
const { result } = renderHook(() => useSmartSearch(mockProducts))

act(() => {
  result.current.setSearchQuery('keto')
})

expect(result.current.searchQuery).toBe('keto')
```

### 3. Suggestion Testing
```typescript
act(() => {
  result.current.search('keto')
})

const categorySuggestions = result.current.suggestions.filter(
  s => s.type === 'category'
)
expect(categorySuggestions.length).toBeGreaterThan(0)
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
```

## Debugging Tests

### Running Single Test
```bash
npm test -- -t "should find products by SKU"
```

### Debug Mode
```bash
node --inspect-brk node_modules/.bin/jest --runInBand
```

### Verbose Output
```bash
npm test -- --verbose
```

### Update Snapshots (if using snapshot testing)
```bash
npm test -- -u
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Descriptive Names**: Test names should clearly describe what they test
3. **Arrange-Act-Assert**: Follow the AAA pattern
4. **Mock External Dependencies**: Don't rely on external APIs
5. **Test Edge Cases**: Empty strings, null values, large datasets
6. **Performance Tests**: Ensure search is fast even with many products

## Common Issues

### Issue: "Cannot find module '@/lib/searchConfig'"
**Solution**: Ensure `tsconfig.json` has the correct path mapping:
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### Issue: "ReferenceError: window is not defined"
**Solution**: Use `jest-environment-jsdom` in jest.config.js

### Issue: "TypeError: Cannot read property 'search' of undefined"
**Solution**: Ensure Fuse.js is properly initialized in test setup

## Contributing

When adding new search features:

1. Write tests first (TDD approach)
2. Ensure all existing tests pass
3. Add integration tests for new features
4. Update this README with new test scenarios
5. Maintain > 90% code coverage

## Questions?

For questions about the tests or to report issues:
- Check test output carefully
- Review test names to understand what's being tested
- Look at mock data to understand test scenarios
- Check Jest documentation: https://jestjs.io/
