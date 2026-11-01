#include <iostream>
#include <algorithm>
using namespace std;

int T,N,x[50];
bool is_used[50];
int sum;
int target;
bool is_ans;

bool cmp(int a , int b)
{
    return a > b;
}

void dfs(int start , int l , int edge)
{
    if(edge == 4)
    {
        is_ans = 1;
        return;
    }
    if(is_ans) return;

    for(int i = start;i<=N;i++)
    {
        if(is_used[i]) continue;
        if(l + x[i] > target) continue;

        is_used[i] = 1;
        if(l + x[i] == target)
        {
            dfs(1 , 0 , edge+1);
        }
        else
        {
            dfs(i+1 , l + x[i] , edge);
        }

        is_used[i] = 0;
    }
}

int main()
{
    cin >> T;

    while(T--)
    {
        is_ans = 0;
        sum = 0;
        target = 0;
        cin >> N;
        for(int i = 1;i<=N;i++)
        {
            cin >> x[i];
            sum += x[i];
        }



        if(sum % 4) 
        {
            printf("no\n");
            continue;
        }

        sort(x+1 , x+1+N , cmp);

        target = sum / 4;
        dfs(1 , 0 , 1);

        if(is_ans) printf("yes\n");
        else printf("no\n");
    }
    return 0;
}