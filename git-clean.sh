#!/bin/bash

echo "🧹 Starting safe cleanup across all repositories..."

for repo in devops-dogops-app devops-dogops-gitops devops-dogops-infra; do
  echo -e "\n======================================="
  echo "📁 Repository: $repo"
  echo "======================================="
  
  cd ~/github-projects/$repo || { echo "❌ Directory not found!"; continue; }

  # מעבר ל-master ומשיכת עדכונים
  git checkout master 2>/dev/null
  git pull origin master

  # סנכרון מול גיטהאב וסימון ענפים שנמחקו בענן (Pruning)
  git fetch -p

  # הטריק הבטוח: מוצא רק ענפים מקומיים שהענף שלהם בגיטהאב נמחק (מסומנים כ-gone)
  # ומוחק אותם. כל ענף אחר שנמצא בפיתוח - לא ייפגע!
  BRANCHES_TO_DELETE=$(git branch -vv | awk '/: gone]/{print $1}')
  
  if [ -z "$BRANCHES_TO_DELETE" ]; then
    echo "✨ No merged branches to clean here."
  else
    echo "🗑️ Deleting cleaned branches:"
    echo "$BRANCHES_TO_DELETE" | xargs -n 1 git branch -D
  fi

done

echo -e "\n✅ All environments are clean and ready for the next feature!"