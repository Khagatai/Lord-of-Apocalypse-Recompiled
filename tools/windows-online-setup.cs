// SPDX-License-Identifier: GPL-3.0-or-later
// Small Windows installer. No game content or credentials are embedded.
using System;
using System.Collections.Generic;
using System.Diagnostics;
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
public sealed class PackageManifest { public int schema; public string version; public bool game_payloads_included,builds_native_game_locally; public InstalledFile[] files; }
public sealed class UpdateEntry { public string path; public bool existed; }
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
    static void CheckSpace(SetupManifest m,string parent,string cache,string adjacent,bool upgrade){
        long downloads=0;
        foreach(var a in m.assets)if(!Matches(Path.Combine(adjacent,a.name),a)&&!Matches(Path.Combine(cache,a.name),a))downloads+=a.size;
        var targetDrive=new DriveInfo(Path.GetPathRoot(parent));var cacheDrive=new DriveInfo(Path.GetPathRoot(cache));
        long install=m.expanded_size+(upgrade?0:Math.Max(2300L*1024*1024,m.local_build_extra_bytes));
        if(String.Equals(targetDrive.Name,cacheDrive.Name,StringComparison.OrdinalIgnoreCase)){
            if(targetDrive.AvailableFreeSpace<install+downloads)throw new IOException(upgrade?
                "Not enough free space for the update download and temporary package files.":
                "Not enough free space. Allow room for downloads, native compilation, the English image and generated HD textures. The ISO-only build needs about 18 GB of free space.");
        }else if(targetDrive.AvailableFreeSpace<install||cacheDrive.AvailableFreeSpace<downloads+64L*1024*1024)throw new IOException("Not enough free space on the installation or download drive.");
    }
    public static void Install(SetupManifest manifest,string target,string cache,string adjacent,Action<SetupProgress> report,CancellationToken token,bool test,bool upgrade=false){
        Validate(manifest,test);token.ThrowIfCancellationRequested();target=Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar);
        cache=Path.GetFullPath(cache);adjacent=Path.GetFullPath(adjacent);
        if(!Ascii(target)||target==Path.GetPathRoot(target).TrimEnd(Path.DirectorySeparatorChar))throw new IOException("Choose an ASCII-only game folder, not a drive root.");
        if(File.Exists(target)||(Directory.Exists(target)&&Directory.GetFileSystemEntries(target).Length!=0))throw new IOException("Choose a new or empty folder. Existing games, saves and preferences will not be overwritten.");
        string parent=Path.GetDirectoryName(target);Directory.CreateDirectory(parent);Directory.CreateDirectory(cache);CheckSpace(manifest,parent,cache,adjacent,upgrade);
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

    static string ManagedPath(string root,string name){
        string[] parts=(name??"").Split('/');
        string[] allowed={"tools/","config/","licenses/","external/nakagawa-recomp/","private/tools/python314/","private/tools/pspdecrypt/",
            "private/toolchain/prerequisites/msys64/ucrt64/","private/distribution/recipes/","private/steam-test/","private/online-deps/"};
        bool managed=name=="PACKAGE-MANIFEST.json"||name=="private/distribution/release.json"||name=="LordOfApocalypse.exe"||
            name=="README.md"||name=="READ-ME-FIRST.txt"||name=="LICENSE"||name=="CREDITS.md";
        foreach(var prefix in allowed)if((name??"").StartsWith(prefix,StringComparison.Ordinal))managed=true;
        string path=root;
        foreach(string part in parts){
            if(String.IsNullOrWhiteSpace(part)||part=="."||part==".."||part.EndsWith(".")||part.EndsWith(" ")||
               part.IndexOfAny(Path.GetInvalidFileNameChars())>=0||part.IndexOf('\\')>=0)throw new InvalidDataException("Invalid managed file path.");
            path=Path.Combine(path,part);
            RejectLink(path);
        }
        if(!managed)throw new InvalidDataException("Update attempted to change a non-package file: "+name);
        return path;
    }

    static void RejectLink(string path){
        try{if((File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)throw new IOException("An update path is a link: "+path);}
        catch(FileNotFoundException){}catch(DirectoryNotFoundException){}
    }

    static Dictionary<string,InstalledFile> ManagedFiles(string root,out string version){
        var record=Json<PackageManifest>(File.ReadAllText(ManagedPath(root,"PACKAGE-MANIFEST.json")));
        if(record==null||record.schema!=2||!record.builds_native_game_locally||record.game_payloads_included||record.files==null)
            throw new InvalidDataException("Choose an installation made from the ISO-only player package.");
        var map=new Dictionary<string,InstalledFile>(StringComparer.OrdinalIgnoreCase);
        foreach(var file in record.files){
            ManagedPath(root,file.path);
            if(file.path=="PACKAGE-MANIFEST.json"||file.size<0||!System.Text.RegularExpressions.Regex.IsMatch(file.sha256??"","^[a-f0-9]{64}$")||map.ContainsKey(file.path))
                throw new InvalidDataException("Invalid installed file record.");
            map.Add(file.path,file);
        }
        if(!map.ContainsKey("LordOfApocalypse.exe"))throw new InvalidDataException("The launcher is missing from the package manifest.");
        version=record.version;
        return map;
    }

    static bool Matches(string path,InstalledFile file){return File.Exists(path)&&new FileInfo(path).Length==file.size&&Hash(path)==file.sha256;}

    static int CompareVersions(string left,string right){
        var pattern=new System.Text.RegularExpressions.Regex(@"^([0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6})(?:-(alpha|beta|rc)\.([0-9]{1,6}))?$");
        var a=pattern.Match(left??"");
        var b=pattern.Match(right??"");
        if(!a.Success||!b.Success)throw new InvalidDataException("Unsupported package version.");
        int core=new Version(a.Groups[1].Value).CompareTo(new Version(b.Groups[1].Value));
        if(core!=0)return core;
        string[] order={"alpha","beta","rc",""};
        int channel=Array.IndexOf(order,a.Groups[2].Value)-Array.IndexOf(order,b.Groups[2].Value);
        return channel!=0?channel:Int32.Parse("0"+a.Groups[3].Value).CompareTo(Int32.Parse("0"+b.Groups[3].Value));
    }

    static void Recover(string target,string backup,string journal){
        if(!File.Exists(journal))return;
        var entries=Json<UpdateEntry[]>(File.ReadAllText(journal));
        for(int i=entries.Length-1;i>=0;--i){
            var entry=entries[i];string path=ManagedPath(target,entry.path),saved=ManagedPath(backup,entry.path);
            if(File.Exists(saved)){
                if(File.Exists(path))File.Replace(saved,path,null);else File.Move(saved,path);
            }else if(!entry.existed&&File.Exists(path))File.Delete(path);
        }
        File.Delete(journal);
    }

    public static void Upgrade(SetupManifest manifest,string target,string cache,string adjacent,Action<SetupProgress> report,CancellationToken token,bool test){
        target=Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar);
        if(!Directory.Exists(target)||!File.Exists(Path.Combine(target,"PACKAGE-MANIFEST.json")))
            throw new IOException("Choose the folder that contains your installed launcher.");
        RejectLink(target);
        string launcher=Path.Combine(target,"private","launcher");
        RejectLink(Path.Combine(target,"private"));RejectLink(launcher);
        Directory.CreateDirectory(launcher);
        string journal=Path.Combine(launcher,"update-in-progress.json");
        string pending=journal+".next";
        string backup=Path.Combine(launcher,"update-rollback");
        string owner=Path.Combine(backup,"owner.txt");
        string mutex=Path.Combine(launcher,"session.lock");
        foreach(var file in new[]{journal,pending,backup,owner,mutex})RejectLink(file);
        using(var session=new FileStream(mutex,FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
            if(Directory.Exists(backup)&&(!File.Exists(owner)||File.ReadAllText(owner)!="LOA-update-v1"))
                throw new IOException("An unrelated folder occupies the update backup location.");
            Recover(target,backup,journal);
            string oldVersion,newVersion;
            var old=ManagedFiles(target,out oldVersion);
            string stage=Path.Combine(Path.GetDirectoryName(target),".loa-update-"+Guid.NewGuid().ToString("N").Substring(0,12));
            try{
                Install(manifest,stage,cache,adjacent,report,token,test,true);
                var next=ManagedFiles(stage,out newVersion);
                if(newVersion!=manifest.version)throw new InvalidDataException("Package version differs from the installer.");
                if(CompareVersions(newVersion,oldVersion)<0)throw new InvalidDataException("Setup is older than the installed game.");
                var changes=new List<UpdateEntry>();
                int index=0;
                foreach(var file in next.Values){
                    token.ThrowIfCancellationRequested();
                    string path=ManagedPath(target,file.path);
                    if(!Matches(path,file)){
                        bool exists=File.Exists(path);
                        if(Directory.Exists(path)||(exists&&!old.ContainsKey(file.path)))throw new IOException("A local file occupies the update path: "+file.path);
                        changes.Add(new UpdateEntry{path=file.path,existed=exists});
                    }
                    report(new SetupProgress("Comparing installed files...",++index,next.Count));
                }
                foreach(var file in old.Values)
                    if(!next.ContainsKey(file.path)&&Matches(ManagedPath(target,file.path),file))changes.Add(new UpdateEntry{path=file.path,existed=true});
                if(Hash(ManagedPath(target,"PACKAGE-MANIFEST.json"))!=Hash(ManagedPath(stage,"PACKAGE-MANIFEST.json")))
                    changes.Add(new UpdateEntry{path="PACKAGE-MANIFEST.json",existed=true});
                if(changes.Count==0){report(new SetupProgress("The installation is up to date.",1,1));return;}
                token.ThrowIfCancellationRequested();
                Directory.CreateDirectory(backup);
                File.WriteAllText(owner,"LOA-update-v1");
                using(var file=new FileStream(pending,FileMode.Create,FileAccess.Write,FileShare.None)){
                    byte[] data=Encoding.UTF8.GetBytes(new JavaScriptSerializer{MaxJsonLength=32*1024*1024}.Serialize(changes));
                    file.Write(data,0,data.Length);file.Flush(true);
                }
                File.Move(pending,journal);
                try{
                    index=0;
                    foreach(var change in changes){
                        token.ThrowIfCancellationRequested();
                        string path=ManagedPath(target,change.path),source=ManagedPath(stage,change.path),saved=ManagedPath(backup,change.path);
                        if(change.existed){
                            Directory.CreateDirectory(Path.GetDirectoryName(saved));
                            if(File.Exists(source))File.Replace(source,path,saved);else File.Move(path,saved);
                        }else{
                            Directory.CreateDirectory(Path.GetDirectoryName(path));File.Move(source,path);
                        }
                        report(new SetupProgress("Updating changed files...",++index,changes.Count));
                    }
                    File.Delete(journal);
                }catch{Recover(target,backup,journal);throw;}
                report(new SetupProgress("Update complete. Launch the game when ready.",1,1));
            }finally{
                if(!File.Exists(journal)&&Directory.Exists(backup))Directory.Delete(backup,true);
                if(Directory.Exists(stage))Directory.Delete(stage,true);
            }
        }
    }
}

#if !INSTALLER_TEST
public sealed class SetupWindow:Form {
    TextBox folder=new TextBox();Button browse=new Button(),install=new Button(),cancel=new Button(),launch=new Button();Label status=new Label();ProgressBar progress=new ProgressBar();CheckBox shortcut=new CheckBox();CancellationTokenSource cancellation;bool busy=false;string installed;
    readonly string updateTarget,expectedTag;
    readonly int waitPid;
    public SetupWindow(string target=null,int pid=0,string tag=null){
        updateTarget=target;waitPid=pid;expectedTag=tag;
        Icon=Icon.ExtractAssociatedIcon(Application.ExecutablePath);
        Text="Lord of Apocalypse - Setup";ClientSize=new Size(650,310);FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;StartPosition=FormStartPosition.CenterScreen;Font=new Font("Segoe UI",10);
        var intro=new Label{Text=target==null?"Install Lord of Apocalypse\nSelect your own ISO on first launch to build the game. HD textures are optional.":"Update Lord of Apocalypse\nSetup checks the installed package files and applies changes. Your save files and settings stay in the existing installation.",Location=new Point(20,15),Size=new Size(610,65)};Controls.Add(intro);
        folder.SetBounds(20,90,505,28);folder.Text=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","LordOfApocalypse-Recomp");Controls.Add(folder);
        browse.Text="Browse...";browse.SetBounds(535,88,95,30);browse.Click+=delegate{using(var dialog=new FolderBrowserDialog{Description="Choose a new folder or select an installed copy to update"})if(dialog.ShowDialog()==DialogResult.OK)folder.Text=dialog.SelectedPath;};Controls.Add(browse);
        shortcut.Text="Create a desktop shortcut";shortcut.Checked=true;shortcut.SetBounds(20,125,400,28);Controls.Add(shortcut);
        status.SetBounds(20,165,610,55);status.Text="Ready. Verified local release files are used when available; otherwise they download from GitHub.";Controls.Add(status);
        progress.SetBounds(20,225,610,18);Controls.Add(progress);
        install.Text="Install";install.SetBounds(330,260,95,32);install.Click+=async delegate{await BeginInstall();};Controls.Add(install);
        cancel.Text="Close";cancel.SetBounds(535,260,95,32);cancel.Click+=delegate{if(busy){cancellation.Cancel();status.Text="Cancelling safely...";}else Close();};Controls.Add(cancel);
        launch.Text="Launch game";launch.SetBounds(430,260,100,32);launch.Enabled=false;launch.Click+=delegate{System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(Path.Combine(installed,"LordOfApocalypse.exe")){UseShellExecute=true,WorkingDirectory=installed});};Controls.Add(launch);
        FormClosing+=delegate(object sender,FormClosingEventArgs e){if(busy){e.Cancel=true;cancellation.Cancel();status.Text="Cancelling safely...";}};
        if(target!=null){
            folder.Text=target;folder.ReadOnly=true;browse.Visible=false;shortcut.Visible=false;install.Text="Update";
            Shown+=async delegate{await BeginInstall();};
        }
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
        string target=folder.Text;
        bool upgrade=updateTarget!=null;
        bool existing=false;
        try{existing=File.Exists(Path.Combine(target,"PACKAGE-MANIFEST.json"));}catch(ArgumentException){}
        if(!upgrade&&existing){
            if(MessageBox.Show(this,"Update the existing installation in this folder? Close its launcher and game first.",
                "Lord of Apocalypse Update",MessageBoxButtons.YesNo,MessageBoxIcon.Question,MessageBoxDefaultButton.Button2)!=DialogResult.Yes)return;
            upgrade=true;
        }
        busy=true;install.Enabled=browse.Enabled=folder.Enabled=shortcut.Enabled=false;cancel.Text="Cancel";cancellation=new CancellationTokenSource();
        DateTime last=DateTime.MinValue;
        var reporter=new Progress<SetupProgress>(delegate(SetupProgress p){status.Text=p.message;progress.Style=p.total>0?ProgressBarStyle.Continuous:ProgressBarStyle.Marquee;if(p.total>0)progress.Value=(int)Math.Max(0,Math.Min(100,p.done*100/p.total));});
        try{
            string text;using(var reader=new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("release.json")))text=reader.ReadToEnd();
            SetupManifest manifest=SetupEngine.Json<SetupManifest>(text);string cache=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"LoARecompSetup",manifest.version);
            string adjacent=PayloadDirectory();
            await Task.Run(delegate{
                Action<SetupProgress> progressUpdate=delegate(SetupProgress p){if((DateTime.UtcNow-last).TotalMilliseconds>100||p.done==p.total){((IProgress<SetupProgress>)reporter).Report(p);last=DateTime.UtcNow;}};
                if(!upgrade){SetupEngine.Install(manifest,target,cache,adjacent,progressUpdate,cancellation.Token,false);return;}
                if(expectedTag!=null&&expectedTag!="v"+manifest.version)throw new InvalidDataException("Installer version differs from the selected release.");
                if(waitPid>0){
                    Process previous=null;try{previous=Process.GetProcessById(waitPid);}catch(ArgumentException){}
                    using(previous)if(previous!=null&&!previous.WaitForExit(30000))throw new IOException("Close the game launcher before retrying the update.");
                }
                SetupEngine.Upgrade(manifest,target,cache,adjacent,progressUpdate,cancellation.Token,false);
            });
            installed=Path.GetFullPath(target);launch.Enabled=true;
            if(!upgrade&&shortcut.Checked){try{Shortcut(installed);}catch(Exception e){status.Text="Installed. Desktop shortcut could not be created: "+e.Message;}}
        }catch(OperationCanceledException){status.Text="Installation cancelled. Existing game files and saves were not changed.";}
        catch(Exception e){status.Text=e.Message;MessageBox.Show(this,e.Message,"Installation could not finish",MessageBoxButtons.OK,MessageBoxIcon.Error);}
        finally{busy=false;install.Enabled=browse.Enabled=folder.Enabled=shortcut.Enabled=true;cancel.Text="Close";progress.Style=ProgressBarStyle.Continuous;cancellation.Dispose();}
    }
    [STAThread] public static void Main(string[] args){
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        int pid=0;
        if(args.Length==0)Application.Run(new SetupWindow());
        else if(args.Length==2&&args[0]=="--update")Application.Run(new SetupWindow(args[1]));
        else if(args.Length==6&&args[0]=="--update"&&args[2]=="--wait"&&Int32.TryParse(args[3],out pid)&&args[4]=="--tag")
            Application.Run(new SetupWindow(args[1],pid,args[5]));
        else MessageBox.Show("Use Setup.exe or Setup.exe --update followed by the installation folder.","Lord of Apocalypse Setup");
    }
}
#endif
