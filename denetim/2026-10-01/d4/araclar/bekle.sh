#!/bin/bash
# bekle.sh N : wait up to N seconds (<=300); print worktree branch heads and load at the end
N=${1:-280}
end=$((SECONDS+N))
start=$(git -C /home/user/asd for-each-ref --format='%(refname:short) %(objectname:short)' refs/heads | md5sum)
while [ $SECONDS -lt $end ]; do
  cur=$(git -C /home/user/asd for-each-ref --format='%(refname:short) %(objectname:short)' refs/heads | md5sum)
  :
  read -t 15 < /dev/zero 2>/dev/null || true
  timeout 15 tail -f /dev/null 2>/dev/null
done
date -u +%H:%M:%S; uptime | sed 's/.*load/load/'
git -C /home/user/asd worktree list | sed 's#/home/user/asd/.claude/worktrees/##'
