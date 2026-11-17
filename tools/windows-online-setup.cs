// SPDX-License-Identifier: GPL-3.0-or-later
// Small Windows installer. No game content or credentials are embedded.
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

public sealed class SetupAsset { public string name, url, sha256; public long size; }
public sealed class SetupManifest { public int schema,max_relative_path; public string version; public long expanded_size,local_build_extra_bytes; public SetupAsset[] assets; }
public sealed class InstalledFile { public string path, sha256; public long size; }
public sealed class PackageManifest { public InstalledFile[] files; }
public sealed class SetupProgress {
    public string message; public long done,total;
    public SetupProgress(string text,long current,long length){message=text;done=current;total=length;}
}

public static class SetupEngine {
    const string Prefix="LordOfApocalypse-Recomp/";
    public static string Hash(string path){using(var s=File.OpenRead(path))using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(s)).Replace("-","").ToLowerInvariant();}
    public static T Json<T>(string text){return new JavaScriptSerializer{MaxJsonLength=32*1024*1024}.Deserialize<T>(text);}
    public static bool Matches(string path,SetupAsset a){return File.Exists(path)&&new FileInfo(path).Length==a.size&&Hash(path)==a.sha256;}
    static bool Ascii(string value){foreach(char c in value)if(c>127)return false;return true;}
    public static void Validate(SetupManifest m,bool test){
        if(m==null||m.schema!=1||m.assets==null||m.assets.Length<1||m.assets.Length>32||m.expanded_size<1)throw new InvalidDataException("Invalid installer manifest.");
        var names=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach(var a in m.assets){
            Uri uri;
            if(a==null||String.IsNullOrEmpty(a.name)||Path.GetFileName(a.name)!=a.name||a.name.IndexOfAny(Path.GetInvalidFileNameChars())>=0||a.name=="."||a.name==".."||!names.Add(a.name)||a.size<1||a.size>=2L*1024*1024*1024||!System.Text.RegularExpressions.Regex.IsMatch(a.sha256??"","^[a-f0-9]{64}$")||!Uri.TryCreate(a.url,UriKind.Absolute,out uri))throw new InvalidDataException("Invalid download record.");
            if(!(uri.Scheme=="https"&&uri.Host=="github.com"&&uri.AbsolutePath.StartsWith("/Khagatai/Lord-of-Apocalypse-Recompiled/releases/download/",StringComparison.Ordinal))&&!(test&&uri.IsLoopback&&uri.Scheme=="http"))throw new InvalidDataException("Unexpected download location.");
        }
    }
    static void Download(SetupAsset a,string path,Action<SetupProgress> report,CancellationToken token){
        string partial=path+".part";
        if(File.Exists(partial)&&new FileInfo(partial).Length>a.size)File.Delete(partial);
        long offset=File.Exists(partial)?new FileInfo(partial).Length:0;
        if(offset==a.size){if(Hash(partial)==a.sha256){File.Move(partial,path);return;}File.Delete(partial);offset=0;}
        ServicePointManager.SecurityProtocol=SecurityProtocolType.Tls12;
        var request=(HttpWebRequest)WebRequest.Create(a.url);request.UserAgent="LordOfApocalypse-Setup/1";request.Timeout=20000;request.ReadWriteTimeout=30000;
        if(offset>0)request.AddRange(offset);
        try{
            using(token.Register(delegate{request.Abort();}))
            using(var response=(HttpWebResponse)request.GetResponse()){
                if(response.ResponseUri.Scheme!="https"&&!response.ResponseUri.IsLoopback)throw new InvalidDataException("Download redirected to an insecure location.");
                if(offset>0&&response.StatusCode==HttpStatusCode.PartialContent){
                    string expected="bytes "+offset+"-";
                    if(!(response.Headers["Content-Range"]??"").StartsWith(expected,StringComparison.Ordinal))throw new InvalidDataException("Invalid resumed download range.");
                } else if(response.StatusCode==HttpStatusCode.OK){offset=0;}
                else throw new InvalidDataException("Unexpected download response.");
                using(var input=response.GetResponseStream())using(var output=new FileStream(partial,offset==0?FileMode.Create:FileMode.Append,FileAccess.Write,FileShare.None)){
                    byte[] buffer=new byte[512*1024];int count;
                    while((count=input.Read(buffer,0,buffer.Length))>0){token.ThrowIfCancellationRequested();if(offset+count>a.size)throw new InvalidDataException("Download is larger than expected.");output.Write(buffer,0,count);offset+=count;report(new SetupProgress("Downloading "+a.name,offset,a.size));}
                }
            }
        }catch(WebException e){
            token.ThrowIfCancellationRequested();
            var response=e.Response as HttpWebResponse;
            if(response!=null&&response.StatusCode==HttpStatusCode.NotFound)throw new IOException("The release files have not been published at the download address yet. Retry after publication, or place all release ZIPs beside Setup.exe.",e);
            throw new IOException("Download failed. Your partial download is kept so you can retry. "+e.Message,e);
        }
        token.ThrowIfCancellationRequested();report(new SetupProgress("Verifying download...",0,0));
        if(!Matches(partial,a)){File.Delete(partial);throw new InvalidDataException("Download verification failed for "+a.name+". No game files were installed.");}
        File.Move(partial,path);
    }
    static void CheckSpace(SetupManifest m,string parent,string cache,string adjacent){
        long downloads=0;
        foreach(var a in m.assets)if(!Matches(Path.Combine(adjacent,a.name),a)&&!Matches(Path.Combine(cache,a.name),a))downloads+=a.size;
        var targetDrive=new DriveInfo(Path.GetPathRoot(parent));var cacheDrive=new DriveInfo(Path.GetPathRoot(cache));
        long install=m.expanded_size+Math.Max(2300L*1024*1024,m.local_build_extra_bytes);
        if(String.Equals(targetDrive.Name,cacheDrive.Name,StringComparison.OrdinalIgnoreCase)){
            if(targetDrive.AvailableFreeSpace<install+downloads)throw new IOException("Not enough free space. Allow room for downloads, native compilation, the English image and generated HD textures. The ISO-only build needs about 18 GB of free space.");
        }else if(targetDrive.AvailableFreeSpace<install||cacheDrive.AvailableFreeSpace<downloads+64L*1024*1024)throw new IOException("Not enough free space on the installation or download drive.");
    }
    public static void Install(SetupManifest manifest,string target,string cache,string adjacent,Action<SetupProgress> report,CancellationToken token,bool test){
        Validate(manifest,test);token.ThrowIfCancellationRequested();target=Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar);
        cache=Path.GetFullPath(cache);adjacent=Path.GetFullPath(adjacent);
        if(!Ascii(target)||target==Path.GetPathRoot(target).TrimEnd(Path.DirectorySeparatorChar))throw new IOException("Choose an ASCII-only game folder, not a drive root.");
        if(File.Exists(target)||(Directory.Exists(target)&&Directory.GetFileSystemEntries(target).Length!=0))throw new IOException("Choose a new or empty folder. Existing games, saves and preferences will not be overwritten.");
        string parent=Path.GetDirectoryName(target);Directory.CreateDirectory(parent);Directory.CreateDirectory(cache);CheckSpace(manifest,parent,cache,adjacent);
        string stage=Path.Combine(parent,".loa-setup-"+Guid.NewGuid().ToString("N").Substring(0,12));
        if(manifest.max_relative_path>0&&Math.Max(stage.Length,target.Length)+1+manifest.max_relative_path>=248)throw new IOException("The installation path is too long for this runtime. Choose a shorter ASCII-only folder, such as C:\\Games\\LordOfApocalypse-Recomp.");
        Directory.CreateDirectory(stage);bool installed=false;
        try{
            var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);long expanded=0;
            foreach(var a in manifest.assets){
                token.ThrowIfCancellationRequested();string archivePath=Path.Combine(adjacent,a.name);bool owned=false;
                report(new SetupProgress("Checking "+a.name,0,0));
                if(!Matches(archivePath,a)){
                    archivePath=Path.Combine(cache,a.name);owned=true;
                    if(File.Exists(archivePath)&&!Matches(archivePath,a))File.Delete(archivePath);
                    if(!File.Exists(archivePath))Download(a,archivePath,report,token);
                }
                report(new SetupProgress("Installing "+a.name,0,0));
                using(var archive=ZipFile.OpenRead(archivePath))foreach(var entry in archive.Entries){
                    token.ThrowIfCancellationRequested();
                    if(!entry.FullName.StartsWith(Prefix,StringComparison.Ordinal)||entry.FullName.IndexOf('\\')>=0||((entry.ExternalAttributes>>16)&0xF000)==0xA000)throw new InvalidDataException("Unsafe archive path.");
                    string relative=entry.FullName.Substring(Prefix.Length);
                    string dest=Path.GetFullPath(Path.Combine(stage,relative.Replace('/',Path.DirectorySeparatorChar)));
                    if(!dest.StartsWith(stage+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||relative.IndexOf(':')>=0||!seen.Add(dest))throw new InvalidDataException("Duplicate or unsafe archive path.");
                    if(entry.FullName.EndsWith("/",StringComparison.Ordinal)){Directory.CreateDirectory(dest);continue;}
                    expanded+=entry.Length;if(expanded>manifest.expanded_size)throw new InvalidDataException("Archive expands beyond its expected size.");
                    Directory.CreateDirectory(Path.GetDirectoryName(dest));
                    using(var input=entry.Open())using(var output=new FileStream(dest,FileMode.CreateNew,FileAccess.Write,FileShare.None)){
                        byte[] buffer=new byte[512*1024];int count;long bytes=0;
                        while((count=input.Read(buffer,0,buffer.Length))>0){token.ThrowIfCancellationRequested();output.Write(buffer,0,count);bytes+=count;if(bytes>entry.Length)throw new InvalidDataException("Invalid extracted size.");}
                        if(bytes!=entry.Length)throw new InvalidDataException("Incomplete extracted file.");
                    }
                    report(new SetupProgress("Installing game files...",expanded,manifest.expanded_size));
                }
                if(owned&&File.Exists(archivePath))File.Delete(archivePath);
            }
            var payload=Json<PackageManifest>(File.ReadAllText(Path.Combine(stage,"PACKAGE-MANIFEST.json")));
            if(payload==null||payload.files==null)throw new InvalidDataException("Package file manifest is missing.");
            int index=0;
            foreach(var item in payload.files){
                token.ThrowIfCancellationRequested();string path=Path.GetFullPath(Path.Combine(stage,item.path.Replace('/',Path.DirectorySeparatorChar)));
                if(!path.StartsWith(stage+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||!File.Exists(path)||new FileInfo(path).Length!=item.size||Hash(path)!=item.sha256)throw new InvalidDataException("Installed-file verification failed: "+item.path);
                report(new SetupProgress("Verifying installed files...",++index,payload.files.Length));
            }
            if(!File.Exists(Path.Combine(stage,"LordOfApocalypse.exe")))throw new InvalidDataException("Game launcher is missing.");
            token.ThrowIfCancellationRequested();
            if(Directory.Exists(target))Directory.Delete(target,false);
            Directory.Move(stage,target);installed=true;report(new SetupProgress("Installation complete. Launch the game to select your ISO.",1,1));
        }finally{
            if(!installed&&Directory.Exists(stage)&&Path.GetDirectoryName(stage)==parent&&Path.GetFileName(stage).StartsWith(".loa-setup-",StringComparison.Ordinal))Directory.Delete(stage,true);
        }
    }
}

#if !INSTALLER_TEST
public sealed class SetupWindow:Form {
    TextBox folder=new TextBox();Button browse=new Button(),install=new Button(),cancel=new Button(),launch=new Button();Label status=new Label();ProgressBar progress=new ProgressBar();CheckBox shortcut=new CheckBox();CancellationTokenSource cancellation;bool busy=false;string installed;
    public SetupWindow(){
        Icon=Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        Text="Lord of Apocalypse - Setup";ClientSize=new Size(650,310);FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;StartPosition=FormStartPosition.CenterScreen;Font=new Font("Segoe UI",10);
        var intro=new Label{Text="Install Lord of Apocalypse\nBuild tools download from GitHub. On first launch, your own ISO is used to build the native game, English text and HD textures locally.",Location=new Point(20,15),Size=new Size(610,65)};Controls.Add(intro);
        folder.SetBounds(20,90,505,28);folder.Text=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","LordOfApocalypse-Recomp");Controls.Add(folder);
        browse.Text="Browse...";browse.SetBounds(535,88,95,30);browse.Click+=delegate{using(var dialog=new FolderBrowserDialog{Description="Choose a new or empty folder for the game"})if(dialog.ShowDialog()==DialogResult.OK)folder.Text=dialog.SelectedPath;};Controls.Add(browse);
        shortcut.Text="Create a desktop shortcut";shortcut.Checked=true;shortcut.SetBounds(20,125,400,28);Controls.Add(shortcut);
        status.SetBounds(20,165,610,55);status.Text="Ready. Verified local release files are used when available; otherwise they download from GitHub.";Controls.Add(status);
        progress.SetBounds(20,225,610,18);Controls.Add(progress);
        install.Text="Install";install.SetBounds(330,260,95,32);install.Click+=async delegate{await BeginInstall();};Controls.Add(install);
        cancel.Text="Close";cancel.SetBounds(535,260,95,32);cancel.Click+=delegate{if(busy){cancellation.Cancel();status.Text="Cancelling safely...";}else Close();};Controls.Add(cancel);
        launch.Text="Launch game";launch.SetBounds(430,260,100,32);launch.Enabled=false;launch.Click+=delegate{System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(Path.Combine(installed,"LordOfApocalypse.exe")){UseShellExecute=true,WorkingDirectory=installed});};Controls.Add(launch);
        FormClosing+=delegate(object sender,FormClosingEventArgs e){if(busy){e.Cancel=true;cancellation.Cancel();status.Text="Cancelling safely...";}};
    }
    static string PayloadDirectory(){
        string adjacent=AppDomain.CurrentDomain.BaseDirectory;
        if(Directory.GetFiles(adjacent,"*-part*-of*.zip").Length>0)return adjacent;
        string parent=Path.GetDirectoryName(adjacent.TrimEnd(Path.DirectorySeparatorChar));
        string sibling=Path.Combine(parent,"Setup Files For Github");
        return Directory.Exists(sibling)?sibling:adjacent;
    }
    void Shortcut(string target){
        Type type=Type.GetTypeFromProgID("WScript.Shell");object shell=Activator.CreateInstance(type);object link=type.InvokeMember("CreateShortcut",BindingFlags.InvokeMethod,null,shell,new object[]{Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"Lord of Apocalypse.lnk")});
        try{Type t=link.GetType();t.InvokeMember("TargetPath",BindingFlags.SetProperty,null,link,new object[]{Path.Combine(target,"LordOfApocalypse.exe")});t.InvokeMember("WorkingDirectory",BindingFlags.SetProperty,null,link,new object[]{target});t.InvokeMember("Save",BindingFlags.InvokeMethod,null,link,null);}finally{System.Runtime.InteropServices.Marshal.FinalReleaseComObject(link);System.Runtime.InteropServices.Marshal.FinalReleaseComObject(shell);}
    }
    async Task BeginInstall(){
        busy=true;install.Enabled=browse.Enabled=folder.Enabled=shortcut.Enabled=false;cancel.Text="Cancel";cancellation=new CancellationTokenSource();string target=folder.Text;
        DateTime last=DateTime.MinValue;
        var reporter=new Progress<SetupProgress>(delegate(SetupProgress p){status.Text=p.message;progress.Style=p.total>0?ProgressBarStyle.Continuous:ProgressBarStyle.Marquee;if(p.total>0)progress.Value=(int)Math.Max(0,Math.Min(100,p.done*100/p.total));});
        try{
            string text;using(var reader=new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("release.json")))text=reader.ReadToEnd();
            SetupManifest manifest=SetupEngine.Json<SetupManifest>(text);string cache=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LoARecompSetup",manifest.version);
            string adjacent=PayloadDirectory();
            await Task.Run(delegate{SetupEngine.Install(manifest,target,cache,adjacent,delegate(SetupProgress p){if((DateTime.UtcNow-last).TotalMilliseconds>100||p.done==p.total){((IProgress<SetupProgress>)reporter).Report(p);last=DateTime.UtcNow;}},cancellation.Token,false);});
            installed=Path.GetFullPath(target);launch.Enabled=true;
            if(shortcut.Checked){try{Shortcut(installed);}catch(Exception e){status.Text="Installed. Desktop shortcut could not be created: "+e.Message;}}
        }catch(OperationCanceledException){status.Text="Installation cancelled. Existing game files and saves were not changed.";}
        catch(Exception e){status.Text=e.Message;MessageBox.Show(this,e.Message,"Installation could not finish",MessageBoxButtons.OK,MessageBoxIcon.Error);}
        finally{busy=false;install.Enabled=browse.Enabled=folder.Enabled=shortcut.Enabled=true;cancel.Text="Close";progress.Style=ProgressBarStyle.Continuous;cancellation.Dispose();}
    }
    [STAThread] public static void Main(){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new SetupWindow());}
}
#endif
