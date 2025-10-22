# Frontend Testing Guide

## How to Test the Updated Frontend

### Quick Start

1. **Open the frontend**
   ```bash
   cd /home/ryanreede/projects/photoroom-p-grammetry-poc/frontend
   # Use any local server, for example:
   python3 -m http.server 8080
   # Or if you have Node.js:
   npx http-server -p 8080
   ```

2. **Open in browser**
   ```
   http://localhost:8080
   ```

### Test Scenarios

#### ✅ Test 1: Single Image Upload
1. Click "Select Image" button
2. Choose any image from your computer
3. **Expected:** Image preview appears below
4. **Expected:** "1 image selected" message shows

#### ✅ Test 2: Demo Shoe Button
1. Click "👟 Try a Shoe" button
2. **Expected:** Status message shows "Loading shoe image..."
3. **Expected:** Shoe image preview appears
4. **Expected:** "1 image selected (Demo: Shoe)" message shows
5. **Expected:** Success message appears

#### ✅ Test 3: Demo Mug Button
1. Click "☕ Try a Mug" button
2. **Expected:** Status message shows "Loading mug image..."
3. **Expected:** Mug image preview appears
4. **Expected:** "1 image selected (Demo: Mug)" message shows
5. **Expected:** Success message appears

#### ✅ Test 4: Remove Image
1. Select or load an image
2. Click "× Remove" button under preview
3. **Expected:** Preview disappears
4. **Expected:** "No image selected" message shows

#### ✅ Test 5: Process Button (Without Backend)
1. Enter any text in "Photoroom API Key" field
2. Select an image
3. Click "Generate 3D Model" button
4. **Expected:** Button shows "Processing..." with spinner
5. **Expected:** Status shows "Sending image to server for processing..."
6. **Expected:** After timeout, error message appears (backend not available)
7. **Expected:** Button returns to "Generate 3D Model"

#### ✅ Test 6: Missing API Key
1. Clear API Key field (or skip entering one)
2. Select an image
3. Click "Generate 3D Model"
4. **Expected:** Error message "Please enter your Photoroom API key"

#### ✅ Test 7: Missing Image
1. Don't select any image
2. Click "Generate 3D Model"
3. **Expected:** Error message "Please select an image first"

#### ✅ Test 8: Three.js Viewer
1. **Expected:** Blue rotating cube visible in "3D Preview" section
2. Try dragging with mouse to rotate camera
3. **Expected:** Camera orbits around cube
4. Try mouse wheel to zoom
5. **Expected:** Camera zooms in/out

#### ✅ Test 9: API Key Persistence
1. Enter API key in field
2. Refresh the page
3. **Expected:** API key still filled in (saved to localStorage)

### Visual Verification

Check that all these elements are visible and styled correctly:

- ✅ Header with title "Photogrammetry POC"
- ✅ API key input field
- ✅ Three buttons (Select Image, Try a Shoe, Try a Mug)
- ✅ Three.js viewer with rotating cube
- ✅ Responsive layout on mobile (try resizing browser)

### Browser Console

Open Developer Tools (F12) and check:
- ✅ No JavaScript errors on page load
- ✅ Three.js loads successfully
- ✅ PLYLoader and OBJLoader scripts load
- ✅ When clicking demo buttons, see console logs

### Expected Console Output

When clicking demo buttons, you should see:
```
Shoe image loaded! (or Mug image loaded!)
```

When clicking process (without backend):
```
Error processing image: Failed to fetch
```

### Backend Integration Testing (Future)

Once backend is ready at `http://localhost:8000`:

1. Start backend server
2. Select demo image or upload custom image
3. Enter valid Photoroom API key
4. Click "Generate 3D Model"
5. **Expected:** Loading spinner shows
6. **Expected:** Progress messages appear
7. **Expected:** 3D model loads and replaces cube
8. **Expected:** Model auto-rotates
9. **Expected:** Can orbit/zoom model with mouse

### Troubleshooting

**Images don't load for demo buttons:**
- Check that `img/shoe.jpg` and `img/mug.jpg` exist
- Check browser console for 404 errors

**Three.js doesn't render:**
- Check browser console for errors
- Verify Three.js CDN links are accessible
- Try different browser

**Process button doesn't respond:**
- Check if API key is entered
- Check if image is selected
- Check browser console for errors

**API key doesn't persist:**
- Check if localStorage is enabled in browser
- Check if in private/incognito mode

### Performance Notes

- Image preview is client-side only (no upload until process)
- Three.js uses WebGL (requires GPU support)
- Demo images load from local files (fast)
- Processing depends on backend response time

### Browser Compatibility

Tested/Expected to work on:
- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ⚠️ IE11 (not supported - uses modern JS)

### Next Steps

Once backend is ready:
1. Update `API_ENDPOINT` in `app.js` if needed (currently `http://localhost:8000/process`)
2. Test full integration flow
3. Verify 3D model formats match (PLY or OBJ)
4. Adjust lighting/camera if needed for specific models

