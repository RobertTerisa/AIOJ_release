#include <iostream>
using namespace std;

int n,cnt;
bool is_in_he[100] , is_in_cha[100] , is_in_lie[100];
int map[50];

void modify(int y ,int x)
{
    is_in_he[y+x] = 1;
    is_in_cha[y-x+13] = 1;
    is_in_lie[x] = 1;
    map[y] = x;
}

void reverse(int y , int x)
{
    is_in_he[y+x] = 0;
    is_in_cha[y-x+13] = 0;
    is_in_lie[x] = 0;
    map[y] = 0;
}



void dfs(int x)
{
    if(x > n)
    {
        cnt++;
        if(cnt <= 3)
        {
            for(int i = 1;i<=n;i++) cout << map[i] << ' ';
            cout << '\n';
        }
        
        return;
    }
    
        for(int j = 1;j<=n;j++)
        {
            if(is_in_he[x+j] || is_in_cha[x-j+13] || is_in_lie[j]) continue;

            modify(x , j);
            dfs(x+1);
            reverse(x , j);
        }
    
}

int main()
{
    cin >> n ;
    dfs(1);
    cout << cnt;
    return 0;
}