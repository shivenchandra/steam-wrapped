# Steam Wrapped

A beautiful, Next.js-powered web app and Python backend that generates a "Spotify Wrapped" style summary for your Steam profile.

## Features
- **Total Playtime:** Discover your all-time total hours played.
- **Top 5 Games:** Generates a visually stunning breakdown of your most played games.
- **Backlog Tracker:** Find out how many games you own but have never touched.
- **Generates Cards:** Creates downloadable images with a highly premium glassmorphism theme, ready to share on social media.
- **Vanity URL Support:** Enter your Steam ID or custom community URL directly.

## Setup

1. **Install Python Backend Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure API Keys**
   Create a `.env` file in the root directory and add your Steam Web API Key:
   ```
   STEAM_API_KEY=your_key_here
   ```
   You can get a free key at [https://steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey).

3. **Install Frontend Dependencies**
   ```bash
   npm install
   ```

## Usage

Start both the backend and frontend at the same time:

**Terminal 1 (Backend):**
```bash
venv\Scripts\python api\index.py
```

**Terminal 2 (Frontend):**
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Deploy on Vercel

The app is configured to deploy seamlessly on Vercel. Simply push to GitHub, connect your repository to Vercel, and add the `STEAM_API_KEY` to your Vercel Environment Variables. The Next.js config will automatically proxy requests to the Python serverless functions.

