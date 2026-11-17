// Test-only entry point; never compiled into the public GUI installer.
using System;
using System.IO;
using System.Threading;
public static class SetupTestRunner {
    public static int Main(string[] args){
        try{
            var manifest=SetupEngine.Json<SetupManifest>(File.ReadAllText(args[0]));
            var token=new CancellationTokenSource();if(args.Length>4&&args[4]=="cancel")token.Cancel();
            string previous="";
            SetupEngine.Install(manifest,args[1],args[2],args[3],delegate(SetupProgress p){if(p.message!=previous){Console.WriteLine(p.message);previous=p.message;}},token.Token,true);
            Console.WriteLine("INSTALL_RESULT=PASS");return 0;
        }catch(Exception e){Console.WriteLine(e.GetType().Name+": "+e.Message);return 2;}
    }
}
