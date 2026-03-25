# MediOrbit Frontend Setup Guide

## Prerequisites

- Node.js 16.x or higher
- npm 7.x or higher
- Backend running on `http://localhost:8000` (see BACKEND_SETUP.md)
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Installation Steps

### 1. Navigate to Frontend Directory

```bash
cd frontend
```

### 2. Install Dependencies

```bash
npm install
```

This installs:
- React 19.2.4
- React Router DOM 7.13.1
- Build tools and dev dependencies

**Expected output:**
```
added 1234 packages, and audited 1235 packages in 45s
```

### 3. Verify Installation

```bash
npm list react react-router-dom
```

### 4. Configure API Proxy (Optional)

The API proxy is already configured in `vite.config.js` to proxy `/api` requests to `http://localhost:8000`.

**Current config:**
```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      secure: false
    }
  }
}
```

If backend is on a different URL, update `vite.config.js`:

```javascript
// For production backend
'/api': {
  target: 'https://api.mediorbital.com',
  changeOrigin: true,
  secure: true
}
```

## Running the Frontend

### Development Server

```bash
npm run dev
```

**Expected output:**
```
  VITE v5.0.0  ready in 123 ms

  ➜  Local:   http://localhost:5173/
  ➜  press h + enter to show help
```

**Open in browser**: http://localhost:5173/

### Production Build

```bash
npm run build
```

**Output:**
```
dist/
├── index.html
├── assets/
│   ├── index-*.js
│   ├── index-*.css
│   └── ...
```

### Preview Production Build

```bash
npm run preview
```

Opens preview server at http://localhost:4173/

## Project Structure

```
frontend/
├── index.html                    # Entry HTML
├── vite.config.js               # Vite configuration
├── package.json                 # Dependencies
├── package-lock.json            # Lock file
├── eslint.config.js             # Linting config
├── src/
│   ├── main.jsx                 # React entry point
│   ├── App.jsx                  # Main router component
│   ├── pages/
│   │   ├── HomePage.jsx         # Landing page with chat
│   │   ├── ResultsPage.jsx      # Search results grid
│   │   └── HospitalDetailPage.jsx # Hospital details
│   ├── components/
│   │   ├── ChatWidget.jsx       # Floating chat bubble
│   │   ├── ChatPanel.jsx        # Chat message display
│   │   ├── PrescriptionUpload.jsx # File upload
│   │   ├── HospitalFilters.jsx  # Filter UI
│   │   ├── HospitalCard.jsx     # Hospital card
│   │   ├── HospitalCard.css     # Card styling
│   │   ├── Navbar.jsx           # Navigation header
│   │   ├── Navbar.css           # Navbar styling
│   │   ├── Footer.jsx           # Footer component
│   │   ├── Footer.css           # Footer styling
│   │   ├── ScoreRing.jsx        # Score visualization
│   │   └── __init__.py
│   ├── context/
│   │   └── NavigationAgent.js   # State management context
│   ├── styles/
│   │   ├── globals.css          # Global styles
│   │   └── animations.css       # Animations
│   └── data/
│       └── hospitals.js         # Mock hospital data
└── public/
    └── (Optional static assets)
```

## Styling

### Tailwind CSS Integration

The project uses **Tailwind CSS** utility classes for styling. No separate Tailwind installation needed - utilities are available through the `globals.css`.

**Example usage:**
```jsx
<div className="max-w-7xl mx-auto py-6 px-4">
  <h1 className="text-3xl font-bold text-gray-900">Results</h1>
</div>
```

### Custom CSS

Component-specific styles in `.css` files:
- `HospitalCard.css`: Card layout and animations
- `Navbar.css`: Navigation styling
- `Footer.css`: Footer layout
- `globals.css`: Shared utilities and animations

### Color Scheme

Primary colors:
- Blue: `#2563eb` (blue-600)
- Gray: `#6b7280` (gray-600)
- White: `#ffffff`
- Light Gray: `#f3f4f6` (gray-50)

## Component API Reference

### ChatWidget

```jsx
import ChatWidget from './components/ChatWidget';

// Usage (in App.jsx)
<ChatWidget />
```

**Features**:
- Floating chat bubble toggle
- Sends messages to `/api/chat`
- Processes UI actions
- Handles typing indicators

**Props**: None (uses context for state)

### PrescriptionUpload

```jsx
import PrescriptionUpload from './components/PrescriptionUpload';

// Usage (in App.jsx)
<PrescriptionUpload />
```

**Features**:
- Drag-and-drop file upload
- Calls `/api/parse-prescription`
- Shows extraction results
- Navigates to results

### HospitalCard

```jsx
import HospitalCard from './components/HospitalCard';

// Usage
<HospitalCard hospital={hospitalData} />
```

**Props**:
- `hospital` (object): Hospital data from API

**Features**:
- Displays hospital info
- Shows pricing and stats
- Click to view details
- Hover effects with highlighting

### HospitalFilters

```jsx
import { HospitalFilters } from './components/HospitalFilters';

// Usage
<HospitalFilters filters={filters} onFiltersChange={setFilters} />
```

**Props**:
- `filters` (object): Current filter state
- `onFiltersChange` (function): Callback for filter updates

**Features**:
- Expandable filter sections
- Specialty and city search
- Rating and sort controls

### NavigationAgent Context

```jsx
import { useNavigation } from './context/NavigationAgent';

// Usage in component
const { navigateToResults, navigateToHome, highlightHospital } = useNavigation();

// Dispatch actions
navigateToResults('knee surgery in Chennai');
highlightHospital(hospitalData);
```

**Available Actions**:
- `navigateToResults(query)`: Navigate to results page
- `navigateToHome()`: Go to home
- `navigateToDetail(hospital)`: Navigate to hospital detail
- `highlightHospital(hospital)`: Highlight hospital in view
- `clearHighlight()`: Remove highlight

## API Integration

### Making API Calls

The Vite proxy automatically routes `/api/*` to `http://localhost:8000/api/*`:

```jsx
// No need to specify full URL
const response = await fetch('/api/hospitals?city=Chennai');
const hospitals = await response.json();
```

### Common Patterns

**List Hospitals:**
```jsx
const [hospitals, setHospitals] = useState([]);

useEffect(() => {
  fetch('/api/hospitals?limit=20')
    .then(r => r.json())
    .then(data => setHospitals(data))
    .catch(err => console.error('Error:', err));
}, []);
```

**Get Hospital Details:**
```jsx
const { id } = useParams();

useEffect(() => {
  fetch(`/api/hospitals/${id}`)
    .then(r => r.json())
    .then(data => setHospital(data));
}, [id]);
```

**Send Chat Message:**
```jsx
const sendMessage = async (message) => {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message: message
    })
  });
  
  const data = await response.json();
  setMessages(prev => [...prev, { type: 'bot', text: data.text }]);
  processUIActions(data.actions);
};
```

## Development Workflow

### 1. Start Backend

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### 2. Start Frontend (in new terminal)

```bash
cd frontend
npm run dev
```

### 3. Open App

Visit http://localhost:5173/ in your browser

### 4. Test Features

- **Chat**: Click chat bubble, type a message
- **Search**: Use search chip or type in chat
- **Upload**: Click prescription upload button
- **Filter**: Use filter controls on results page
- **Navigate**: Click hospital cards to view details

### 5. Debug

**Browser DevTools** (F12):
- Console: Log messages and errors
- Network: Monitor API calls
- React DevTools: Inspect component state

**Common Issues**:
- "Failed to fetch": Check backend running on port 8000
- API 404 errors: Verify endpoint names in code
- CORS errors: Check Vite proxy configuration

## Testing

### Manual Testing Checklist

- [ ] Home page loads with chat widget
- [ ] Chat sends message to backend
- [ ] Hospital results display correctly
- [ ] Filters work (specialty, city, etc.)
- [ ] Hospital details page loads
- [ ] Prescription upload accepts files
- [ ] Mobile responsive layout works
- [ ] All links and buttons functional

### Browser Compatibility

Tested on:
- Chrome 120+
- Firefox 121+
- Safari 17+
- Edge 120+

## Performance Optimization

### Code Splitting

React Router automatically code-splits pages. Each page is lazy-loaded when needed.

### Image Optimization

Hospital images use lazy loading:

```jsx
<img src={hospital.heroImage} alt={hospital.name} loading="lazy" />
```

### Bundle Analysis

```bash
npm install -D rollup-plugin-visualizer

# In vite.config.js
import { visualizer } from 'rollup-plugin-visualizer';

export default {
  plugins: [visualizer()]
};

# Then build and open dist/stats.html
```

### Caching

Production build includes hashed filenames for long-term caching:
```
dist/
├── index-a1b2c3d4.js    # Hash changes when content changes
├── style-e5f6g7h8.css
```

## Deployment

### Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel
```

### Deploy to Netlify

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login
netlify login

# Deploy
netlify deploy --prod --dir=dist
```

### Deploy to GitHub Pages

```bash
# Update package.json
"homepage": "https://github.com/username/mediorbital"

# Build
npm run build

# Deploy
gh-pages -d dist
```

## Environment Configuration

### Development

Backend URL: `http://localhost:8000` (via Vite proxy)

### Production

Update API base URL in requests or environment file:

```jsx
// Option 1: Conditional
const API_BASE = process.env.VITE_API_URL || 'https://api.mediorbital.com';

// Option 2: .env file
// .env.production
VITE_API_URL=https://api.mediorbital.com

// Usage in component
const API_URL = import.meta.env.VITE_API_URL;
```

## Troubleshooting

### Issue: Port 5173 already in use

**Solution**:
```bash
npm run dev -- --port 3000  # Use different port
```

### Issue: API requests fail with 404

**Solution**:
- Verify backend running: `curl http://localhost:8000/`
- Check Vite proxy config in `vite.config.js`
- Check endpoint paths in frontend code

### Issue: Styling looks broken

**Solution**:
- Hard refresh: Ctrl+Shift+R (Cmd+Shift+R on Mac)
- Clear browser cache
- Check Tailwind classes are correct

### Issue: State not updating in components

**Solution**:
- Use React DevTools to inspect component state
- Check effect dependencies in useEffect
- Verify context provider is in tree

### Issue: Build fails

**Solution**:
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Then build again
npm run build
```

## Next Steps

1. ✅ Frontend is running on http://localhost:5173/
2. → Verify backend is accessible at http://localhost:8000/
3. → Test chat integration
4. → Test hospital search and filtering
5. → Test prescription upload
6. → Build for production

## Resources

- **React Documentation**: https://react.dev
- **React Router**: https://reactrouter.com
- **Vite Guide**: https://vitejs.dev
- **Tailwind CSS**: https://tailwindcss.com

## Support

For frontend issues:
- Check browser console for errors
- Verify backend API endpoints are accessible
- Inspect network requests in DevTools
- Check component props and state in React DevTools
