#include <iostream>
using namespace std;

int n,k;
int ans[10];
void dfs(int x)
{
    if(x >= n)
    {
        for(int i = 0;i<n;i++)
        {
            cout << ans[i] << ' ';
        }
        cout << '\n';
        return;
    }
    
    for(int i = 1;i<=k;i++)
    {
        ans[x] = i;
        dfs(x+1);
    }
}

int main()
{
    cin >> n >> k;
    dfs(0);
    return 0;
}