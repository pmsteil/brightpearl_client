# fail if any git commits outstanding
if [ -n "$(git status --porcelain)" ]; then
    echo "You have uncommitted changes. Please commit or stash them before tagging."
    exit 1
fi

release="0.1.8"
# tag the current commit
git tag -a v$release -m "Beta release $release"
git push origin v$release
git push
