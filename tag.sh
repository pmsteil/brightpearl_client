# fail if any git commits outstanding
if [ -n "$(git status --porcelain)" ]; then
    echo "You have uncommitted changes. Please commit or stash them before tagging."
    exit 1
fi

# tag the current commit
git tag -a v0.1.4 -m "Beta release 0.1.4"
git push origin v0.1.4
git push
