# Reality TV Air Dates

A free website that shows past, current and upcoming seasons of your reality shows. Once a day, GitHub fetches the latest air dates from [TVmaze](https://www.tvmaze.com/) and republishes the site.

## One-time setup (about 10 minutes)

1. **Create a free GitHub account** at github.com if you don't have one.
2. **Create a new repository.** Click **+** (top right) → **New repository**. Name it something like `reality-tv`, set it to **Public** (Actions and Pages are free for public repos) and click **Create repository**.
3. **Upload the files.** On the new repo's page, click **uploading an existing file**. Drag in *everything from the unzipped folder*, including the hidden `.github` folder. On a Mac, press **Cmd + Shift + .** in Finder to show hidden folders. Click **Commit changes**.
   - If the `.github` folder doesn't upload, create the file by hand: **Add file → Create new file**, type `.github/workflows/update.yml` as the name, paste in the contents of that file, and commit.
4. **Turn on Pages.** Go to **Settings → Pages**. Under **Build and deployment → Source**, choose **GitHub Actions**.
5. **Run it for the first time.** Go to the **Actions** tab. If GitHub asks, click to enable workflows. Pick **Update air dates** → **Run workflow**. Wait about a minute until it shows a green check.
6. **Visit your site** at `https://teferensen.github.io/reality-tv/`. The link also appears in **Settings → Pages**.

After that, it updates itself every morning.

## Adding or removing shows

Edit `shows.json` on GitHub (click the file, then the pencil icon) and commit. The site refreshes right away.

```json
{ "group": "More shows", "name": "Summer House", "country": "US" }
```

- `name` is what TVmaze is searched for, and it's also the title shown on the site.
- `group` is the section heading the show appears under.
- `country` picks the right version when several exist, like the US vs UK *Traitors*.
- **If the wrong show gets matched:** find the right one on tvmaze.com and copy the number from its URL. For example, `tvmaze.com/shows/12345/...` gives `"id": 12345`. Add it to the entry.

Each show card links to the TVmaze page it matched, so you can check it. A ⚠ note on a card means no exact name match was found.

## Good to know

- Each card shows its three most recent seasons, with older ones behind a button. The season that's currently airing is expanded.
- Air times are converted to the viewer's own time zone.
- If GitHub ever says scheduled workflows were disabled for inactivity, open the Actions tab and click **Enable workflow**. The daily data commits usually keep it active.
- Want to refresh right now? **Actions → Update air dates → Run workflow**.
- Schedule data is from TVmaze under CC BY-SA. The footer credit satisfies the license, so leave it in.
