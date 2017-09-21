#!/usr/bin/perl
use strict;
use warnings;
use POSIX;
use Statistics::Regression;
use Getopt::Long;
use File::Basename;

my $kframe_db=dirname($0);
my $kframe_datafile={
    ("1" => $kframe_db."/KFrame_data/KFrame1_170228/byregion.tnt",
     "2" => $kframe_db."/KFrame_data/KFrame2_170503/byregion.tnt")};

# allocate the db array object

my $db=[];
my $usage="USAGE:\t$0 [args] scanfile1 scanfile2 ..\n".
    "\t[args] are any combination of:\n\n".
    "\t--help\n".
    "\t--KFrame=<kframe_id> #(specify KFrame data file drawn from CMM data)\n".
    "\t\tkframe_id options include:\n";

foreach my $kfix (sort keys %{$kframe_datafile}) {
    $usage .= sprintf("\t\t%s for %s\n",$kfix,$kframe_datafile->{$kfix})
}

# process command lines

my $kframe_id=1;
my $help=0;

GetOptions("KFrame=s" => \$kframe_id,
	   "help"     => \$help) || 
    die("error in command line arguments! exiting..\n",$usage);

# get the filename on the commandline

my $filenames=[@ARGV];

my $str="\n";
$str .= sprintf("$0 will run with the following parameters:\n");
$str .= sprintf("\tKFrame id = %s\n",$kframe_id);
$str .= sprintf("\t\t(%s)\n",$kframe_datafile->{$kframe_id});
$str .= sprintf("\tinput files = (%s)\n",join(' ',@{$filenames}));

printf STDERR "%s\n",$str;
if ($help) {
    printf STDERR "%s\n",$usage;
    exit;
}
if (!@{$filenames}) {
    printf STDERR "nothing to do!\n%s\n",$usage;
    exit;
}

foreach my $fn_ix (0..$#{$filenames}) {
    $db->[$fn_ix] = {};
    $db->[$fn_ix]->{"filename"} = $filenames->[$fn_ix];
    read_scan_contents($db->[$fn_ix],{"gain"=>{"key_z1"=>cos((24.0/2.0)*atan2(1,1)/45.0),
						   "key_z2"=>cos((17.0/2.0)*atan2(1,1)/45.0)}});
    # check for presence of a transform spec and provide "raft" coordinate system columns.
    if (defined($db->[$fn_ix]->{"TF"})) {
	my ($x0,$y0,$theta)=($db->[$fn_ix]->{"TF"}->{"X0"},
			     $db->[$fn_ix]->{"TF"}->{"Y0"},
			     $db->[$fn_ix]->{"TF"}->{"theta"});
	my ($raft_x,$raft_y)=([],[]);
	my ($sn,$cs)=(sin($theta*atan2(1,1)/45.0),cos($theta*atan2(1,1)/45.0));
	my ($xv,$yv)=($db->[$fn_ix]->{"aero_x"},$db->[$fn_ix]->{"aero_y"});
	for (my $ix=0;$ix<$db->[$fn_ix]->{"n_entry"};$ix++) {
	    $raft_x->[$ix] = +($xv->[$ix]-$x0)*$cs+($yv->[$ix]-$y0)*$sn;
	    $raft_y->[$ix] = -($xv->[$ix]-$x0)*$sn+($yv->[$ix]-$y0)*$cs;
	}
	append_column($db->[$fn_ix],"raft_x",$raft_x);
	append_column($db->[$fn_ix],"raft_y",$raft_y);
    } # if there's no transformation specs in the input file, this won't affect functionality of this code so continue.
    
    append_sum($db->[$fn_ix],["key_z1","key_z2"],"key_zsum");
    append_column($db->[$fn_ix],"I",[(1)x$db->[$fn_ix]->{"n_entry"}]);
    split_reref_meas($db->[$fn_ix],["_reref","_meas"],"REREF");
    populate_reref_regressions($db->[$fn_ix],"_reref",["I","aero_x","aero_y"],"key_zsum","timestamp");
    populate_ref_system($db->[$fn_ix],["_reref","_meas"],"key_zsum_ref","timestamp");
    append_diff($db->[$fn_ix],["key_zsum","key_zsum_ref"],"key_zsum_ref_rr");

    if (1) {
	foreach my $dep ( "key_z1","key_z2" ) {
	    my $rgr_name = "_".$dep."_regr";
	    my $newcol_name = $dep."_rr";
	    regr_windowed_surface($db->[$fn_ix],$rgr_name,
				  ["I","aero_x","aero_y"],$dep,
				  $db->[$fn_ix]->{"_meas"},1.5);
	    remove_regression($db->[$fn_ix],$rgr_name,$newcol_name);
	}
    }

    # as a sanity check, output a visualization of the structure that is removed by the rereferencing step

    regr_windowed_surface($db->[$fn_ix],"_refsys_regr",
			  ["I","aero_x","aero_y"],"key_zsum_ref",
			  $db->[$fn_ix]->{"_meas"},30);
    remove_regression($db->[$fn_ix],"_refsys_regr","reref_noise");
    
    
    # make up another lateral coordinate system close to the appropriate 
    # kinematic mount support frame model. origin is as shown in marked up KFrame drawing
    if (defined($db->[$fn_ix]->{"TF"})) {
	my $tf=$db->[$fn_ix]->{"TF"};
	append_trans_coords($db->[$fn_ix],
			    ["KF_x","KF_y"],
			    {"raft_offset" => [$tf->{"X0"},$tf->{"Y0"}],
				 "theta" => $tf->{"theta"}*atan2(1,1)/45.0,
				 "MCS_offset" => [113.5/2.0-5.5,0]},
			    ["aero_x","aero_y"]);
    } else {
	# use hardcoded values from ts7-2 as a placeholder
	append_trans_coords($db->[$fn_ix],
			    ["KF_x","KF_y"],
			    {"raft_offset" => [8.25,-19.125],
				 "theta" => 0.242*atan2(1,1)/45.0,
				 "MCS_offset" => [113.5/2.0-5.5,0]},
			    ["aero_x","aero_y"]);
    }
    if (1) {
	# and add in a radial coordinate for the {"KF_x","KF_y"} system..
	my $KF_r=[];
	for (my $i=0;$i<$db->[$fn_ix]->{"n_entry"};$i++) {
	    $KF_r->[$i] = sqrt(pow($db->[$fn_ix]->{"KF_x"}->[$i]-(-(113.5/2.0-5.5)),2)+
			       pow($db->[$fn_ix]->{"KF_y"}->[$i],2));
	}
	append_column($db->[$fn_ix],"KF_r",$KF_r);
    }
    # sample the CMM measured KMSF about 3 positions that we'll use to define a new plane
    # on the way to transfering TS5 measurements into absolute image height.
    my $cmm_BPref_file=$kframe_datafile->{$kframe_id};
    my $tmpdb={};
    $tmpdb->{"filename"}=$cmm_BPref_file;
    read_scan_contents($tmpdb);
    append_column($tmpdb,"I",[(1)x$tmpdb->{"n_entry"}]);

    my $cmm_BPref_lc=["xreq","yreq"];
    my $cmm_BPref_zc="zsum_ballplane_rr";
    my $radial_tol=6; # tolerance for filtering fiducials' sampling

    regr_sample_rgns($tmpdb,"_fidplane",$cmm_BPref_lc,
		     ["I",@{$cmm_BPref_lc}],$cmm_BPref_zc,
		     [[-138.2,20],[-138.2,-20],[34.3,0]],$radial_tol);

    regr_sample_rgns($db->[$fn_ix],"_fidplane",["KF_x","KF_y"],
		     ["I","KF_x","KF_y"],"key_zsum_ref_rr",
		     [[-138.2,20],[-138.2,-20],[34.3,0]],$radial_tol);

    regression_difference($db->[$fn_ix],"_ballplane_rel",
			  ["I","KF_x","KF_y"],"key_zsum_ref_rr",
			  $db->[$fn_ix]->{"_fidplane"}->{"regr"}->{"theta"},
			  $tmpdb->{"_fidplane"}->{"regr"}->{"theta"});

    remove_regression($db->[$fn_ix],"_ballplane_rel","TS5_CMM_ballplane_ref");

    # compute the windowed regression for this last TS5_CMM_ballplane_ref 
    # which should throw out
    # outliers that exceed some number of sigma.

    regr_windowed_surface($db->[$fn_ix],
			  "_windowed_ts5_cmm_ballplane_ref",
			  ["I","KF_x","KF_y"],"TS5_CMM_ballplane_ref",
			  $db->[$fn_ix]->{"_meas"},1.5);
    
    remove_regression($db->[$fn_ix],"_windowed_ts5_cmm_ballplane_ref","TS5_CMM_ballplane_ref_rr");

    # for each label being output, compute regression for each surface using the TS5_CMM_ballplane_ref representation
    # tabulate and subtract. This should subtract out the solid body contribution and leave in surface distortions..
    # this is a higher level of analysis and should produce handsome plots.

    regr_by_labels($db->[$fn_ix],"_rgr_bylabel",["I","KF_x","KF_y"],"TS5_CMM_ballplane_ref",$db->[$fn_ix]->{"_meas"},1.5);
    
    # check out this regression.
    remove_regression($db->[$fn_ix],"_fidplane","fiducialsamp_rr");

    describe_contents($db->[$fn_ix]);
    export_file($db->[$fn_ix],$filenames->[$fn_ix]."__ms.tnt",["label","I"],$db->[$fn_ix]->{"_meas"});

    { # the following moves the output file back to this working directory for jh to register the output file to the catalog
	my $cmd=sprintf("mv %s .",$filenames->[$fn_ix]."__ms.tnt");
	`$cmd`;
    }
    
    remove_regression($tmpdb,"_fidplane","fiducialsamp_rr");
    export_file($tmpdb,"kmsf_temp.tnt",["I"],[0..$tmpdb->{"n_entry"}-1]);
}

sub save_regressions {
    my ($this,$output_filename)=@_;
    open(GG,">",$output_filename) || die;
    printf GG "regressions performed for file %s:\n",$this->{"filename"};
    foreach my $key (sort keys %{$this}) {
	if ((ref $this->{$key} eq ref {}) &&
	    defined($this->{$key}->{"regr"})) {
	    printf GG "\tregression named %s measured against %s:\n",$key,$this->{$key}->{"regr"}->{"regr_dep_axis"};
	    printf GG "\t\tindep: %s\n",join("\t",@{$this->{$key}->{"regr"}->{"regr_indep_axes"}});
	    printf GG "\t\tpars: %s\n",join("\t",@{$this->{$key}->{"regr"}->{"theta"}});
	} else {
	    # it's not a hash or the hash doesn't contain member "regr"
	}
    }
    # now look for special key called "_reref"
    if (defined($this->{"_reref"}) && (ref $this->{"_reref"} eq ref [])) {
	printf GG "rereferencing performed:\n";
	foreach my $entry (@{$this->{"_reref"}}) {
	    if (defined($entry->{"regr"})) {
		my $st=$entry->{"regr"}->{"sort_term"};
		printf GG "! for %s : %s\n",$st,join("\t",@{$entry->{"regr"}->{"regr_indep_axes"}});
		printf GG "%s %s\n",$entry->{"regr"}->{$st},join("\t",@{$entry->{"regr"}->{"theta"}});
	    }
	}
    }
    close(GG);
}

sub remove_regression {
    my ($this,$regr,$newcolname)=@_;
    my $newcol=[];

    my $indep_axes=$this->{$regr}->{"regr"}->{"regr_indep_axes"};

    for (my $i=0;$i<$this->{"n_entry"};$i++) {
	my $regr_value=0;
	foreach my $col_ix (0..$#{$indep_axes}) {
	    my $col=$indep_axes->[$col_ix];
	    $regr_value += ($this->{$regr}->{"regr"}->{"theta"}->[$col_ix] *
			    $this->{$col}->[$i]);
	}
	$newcol->[$i] = $this->{$this->{$regr}->{"regr"}->{"regr_dep_axis"}}->[$i] - $regr_value;
    }
    append_column($this,$newcolname,$newcol);
}

sub regr_by_labels {
    my ($this,$new_regr_root,$regr_indep_axes,$regr_dep_axis,$starting_ix_list,$thresh_rms)=@_;
    #	    ($db->[$fn_ix],"_rgr_bylabel",["I","KF_x","KF_y"],"TS5_CMM_ballplane_ref",$db->[$fn_ix]->{"_meas"},1.5);

    if (!defined($this)) {
	printf STDERR "entry $this doesn't exist.\nexiting..\n";
	exit(1);	}
    if (!defined($this->{$regr_dep_axis})) {
	printf STDERR "dependent axis $regr_dep_axis not defined in $this.\nexiting..\n";
	exit(1);	}
    foreach my $ia (@{$regr_indep_axes}) {
	if (!defined($this->{$ia})) {
	    printf STDERR "independent axis $ia not defined in $this.\nexiting..\n";
	    exit(1);	    }	}
    # go through the list, generate regressions as needed
    my $ix_list=[@{$starting_ix_list}];
    my $iter=0;
    my $nrej=0;
    my $last_nrej=0;
    my $rms={};
    my $rgrs={};
    my $stable_rejection;
    do {
	$nrej=0;
	my $rgressn={};
	my %labs=();
	foreach my $ix (@{$ix_list}) {
	    my ($data,$model)=(0,0);
	    my $lab=$this->{"label"}->[$ix];
	    $labs{$lab}=1;
	    my $new_rgr=$new_regr_root."_".$lab;
	    if (!defined($this->{$new_rgr})) {
		$this->{$new_rgr}={};
		$this->{$new_rgr}->{"regr"}={};
		my $rgr=$this->{$new_rgr}->{"regr"};
		$rgr->{"regr_indep_axes"}=$regr_indep_axes;
		$rgr->{"regr_dep_axis"}=$regr_dep_axis;
		$rgrs->{$lab}=$rgr;
	    }
	    if (!defined($rgressn->{$lab})) {
		$rgressn->{$lab}=Statistics::Regression->new($regr_dep_axis,
							     $regr_indep_axes);
	    }
	    my $rgr=$rgrs->{$lab};
	    if ($iter!=0) {
		($data,$model)=($this->{$rgr->{"regr_dep_axis"}}->[$ix],0);
		foreach my $ia_ix (0..$#{$rgr->{"regr_indep_axes"}}) {
		    my $ia_val=$this->{$rgr->{"regr_indep_axes"}->[$ia_ix]}->[$ix];
		    my $rgr_coeff=$rgr->{"theta"}->[$ia_ix];
		    $model += $ia_val*$rgr_coeff;
		}
	    }
	    if (($iter==0)||(sqrt(pow(($data-$model)/$rms->{$lab},2))<$thresh_rms)) {
		my $datlist=[];
		foreach my $ia (@{$rgr->{"regr_indep_axes"}}) {
		    push(@{$datlist},$this->{$ia}->[$ix]);
		}
		$rgressn->{$lab}->include($this->{$regr_dep_axis}->[$ix],$datlist);
	    } else {
		$nrej++;
	    }
	}
	$stable_rejection=($nrej==$last_nrej)?1:0;
	$last_nrej=$nrej;
	foreach my $lab (keys %labs) {
	    $rms->{$lab} = sqrt($rgressn->{$lab}->sigmasq()+pow(1e-3,2));
	    my $rgr=$rgrs->{$lab};
	    $rgr->{"theta"}=[$rgressn->{$lab}->theta()];
	}
	$iter++;
    } while (($iter<=2) || ($stable_rejection!=1));
    # regressions are stored
    # now since the regression is patchwork, store columns corresponding to the regression and the residuals here, and append them to $this
    {
	# these are the columns that can be appended
	my ($newcol_regmodel,$newcol_regmodelsub)=([],[]); 
	foreach my $ix (@{$ix_list}) {
	    my $lab=$this->{"label"}->[$ix];
	    my $rgr=$rgrs->{$lab};
	    my ($data,$model)=($this->{$regr_dep_axis}->[$ix],0);
	    foreach my $ia_ix (0..$#{$regr_indep_axes}) {
		my $ia_val=$this->{$regr_indep_axes->[$ia_ix]}->[$ix];
		my $rgr_coeff=$rgr->{"theta"}->[$ia_ix];
		$model += $ia_val*$rgr_coeff;
	    }
	    # ready to store
	    $newcol_regmodel->[$ix]=$model;
	    $newcol_regmodelsub->[$ix]=($data-$model);
	}
	append_column($this,$regr_dep_axis."_pwl",$newcol_regmodel);
	append_column($this,$regr_dep_axis."_pwl_rr",$newcol_regmodelsub);
    }
}

sub regr_windowed_surface {
    my ($this,$new_rgr,$regr_indep_axes,$regr_dep_axis,$starting_ix_list,$thresh_rms)=@_;

    if (!defined($this)) {
	printf STDERR "entry $this doesn't exist.\nexiting..\n";
	exit(1);
    }

    if (!defined($this->{$regr_dep_axis})) {
	printf STDERR "dependent axis $regr_dep_axis not defined in $this.\nexiting..\n";
	exit(1);
    }
    foreach my $ia (@{$regr_indep_axes}) {
	if (!defined($this->{$ia})) {
	    printf STDERR "independent axis $ia not defined in $this.\nexiting..\n";
	    exit(1);
	}
    }

    $this->{$new_rgr}={};
    $this->{$new_rgr}->{"regr"}={};
    my $rgr=$this->{$new_rgr}->{"regr"};
    $rgr->{"regr_indep_axes"}=$regr_indep_axes;
    $rgr->{"regr_dep_axis"}=$regr_dep_axis;
    my $ix_list=[@{$starting_ix_list}];
    my $iter=0;
    my $nrej=0;
    my $last_nrej=0;
    my $rms;
    my $stable_rejection;
    do {
	my $rgressn=Statistics::Regression->new($regr_dep_axis,$regr_indep_axes);
	$nrej=0;
	foreach my $ix (@{$ix_list}) {
	    my ($data,$model)=(0,0);
	    if ($iter!=0) {
		($data,$model)=($this->{$rgr->{"regr_dep_axis"}}->[$ix],0);
		foreach my $ia_ix (0..$#{$rgr->{"regr_indep_axes"}}) {
		    my $ia_val = $this->{$rgr->{"regr_indep_axes"}->[$ia_ix]}->[$ix];
		    my $rgr_coeff=$rgr->{"theta"}->[$ia_ix];
		    $model += $ia_val*$rgr_coeff;
		}
	    }
	    if (($iter==0)||(sqrt(pow(($data-$model)/$rms,2))<$thresh_rms)) {
		my $datlist=[];
		foreach my $ia (@{$rgr->{"regr_indep_axes"}}) {
		    push(@{$datlist},$this->{$ia}->[$ix]);
		}
		$rgressn->include($this->{$regr_dep_axis}->[$ix],$datlist);
	    } else {
		$nrej++;
	    }
	}
	$stable_rejection=($nrej==$last_nrej)?1:0;
	$last_nrej=$nrej;
	$rms = sqrt($rgressn->sigmasq()+ pow(1e-3,2));
	$rgr->{"theta"}=[$rgressn->theta()];
	$iter++;
    } while (($iter<=2) || ($stable_rejection!=1));
    # regression is already stored. return control to caller.
}

sub regression_difference {
    my ($this,$new_regr,$regr_indep_axes,$regr_dep_axis,$r1,$r2)=@_;
    $this->{$new_regr}={};
    $this->{$new_regr}->{"regr"}={};
    my $rgr=$this->{$new_regr}->{"regr"};
    $rgr->{"regr_indep_axes"}=$regr_indep_axes;
    $rgr->{"regr_dep_axis"}=$regr_dep_axis;
    
    my $diff=[];
    foreach my $r_ix (0..$#{$r1}) {
	$diff->[$r_ix] = $r1->[$r_ix] - $r2->[$r_ix];
    }
    $rgr->{"theta"}=$diff;
    return($diff);
}
    
sub regr_sample_rgns {
    my ($thedb,$rgr,$lc,$indep_axes,$dep_axis,$samp_lc,$tol)=@_;
    if (!defined($thedb->{$lc->[0]}) || 
	!defined($thedb->{$lc->[1]}) ||
	!defined($thedb->{$dep_axis})) {
	printf STDERR "either $lc->[0], $lc->[1] or $dep_axis are not defined in $thedb.\n";
	printf STDERR "exiting..\n";
	exit(1);
    }
    foreach my $ia (@{$indep_axes}) {
	if (!defined($thedb->{$ia})) {
	    printf STDERR "$ia is not defined in $thedb.\n";
	    printf STDERR "exiting..\n";
	    exit(1);
	}
    }
    

    my $regr_indep_axes=$indep_axes;
    my $regr_dep_axis=$dep_axis;
    my $rgressn=Statistics::Regression->new($regr_dep_axis,$regr_indep_axes);
    for (my $i=0;$i<$thedb->{"n_entry"};$i++) {
	# compute distance to sampling point(s). Include if accepted.
	my $accept=0;
	foreach my $sample_coord (@{$samp_lc}) {
	    my $r2=0;
	    foreach my $coord_ix (0..$#{$lc}) {
		$r2 += pow(($thedb->{$lc->[$coord_ix]}->[$i]-
			    $sample_coord->[$coord_ix]),2);
	    }
	    if ($r2 < pow($tol,2)) {
		$accept=1;
		last;
	    }
	}
	if ($accept==1) {
	    my $dep=$thedb->{$regr_dep_axis}->[$i];
	    my %indep=();
	    for (my $ria_ix=0;$ria_ix<=$#{$regr_indep_axes};$ria_ix++) {
		$indep{$regr_indep_axes->[$ria_ix]}=
		    $thedb->{$regr_indep_axes->[$ria_ix]}->[$i];
	    }
	    $rgressn->include($dep,[@indep{@{$regr_indep_axes}}]);
      }
    }

    # package up results in $thedb->{$rgr}
    my $result_rgr = [$rgressn->theta()];
    $thedb->{$rgr}={};
    $thedb->{$rgr}->{"regr"}={};
    $thedb->{$rgr}->{"regr"}->{"regr_indep_axes"}=$regr_indep_axes;
    $thedb->{$rgr}->{"regr"}->{"regr_dep_axis"}=$regr_dep_axis;
    $thedb->{$rgr}->{"regr"}->{"theta"}=$result_rgr;

    printf STDERR "%s\n",join(' ',@{$result_rgr});
    return([$rgressn->theta()]);
}

sub append_trans_coords {
    my ($this,$new_lat_coords,$trans_spec,$lat_coords)=@_;
    my @lc = ($this->{$lat_coords->[0]},$this->{$lat_coords->[1]});
    my @nlc=([],[]);
    my $theta = $trans_spec->{"theta"};
    my ($sn,$cs)=(sin($theta),cos($theta));
    for (my $i=0;$i<$this->{"n_entry"};$i++) {
	# subtract off raft_offset prior to reversing the rotation. 
	# then apply the MCS offset.
	my $coord=[];
	foreach my $cix (0,1) {
	    $coord->[$cix] = $lc[$cix]->[$i]-$trans_spec->{"raft_offset"}->[$cix];
	}
	($nlc[0]->[$i],
	 $nlc[1]->[$i])=(($coord->[0]*$cs+$coord->[1]*$sn)
			 -$trans_spec->{"MCS_offset"}->[0],
			 (-$coord->[0]*$sn+$coord->[1]*$cs)
			 -$trans_spec->{"MCS_offset"}->[1]);
    }
    foreach my $cix (0,1) {
	append_column($this,$new_lat_coords->[$cix],$nlc[$cix]);
    }
}

sub export_file {
    my ($this,$output_filename,$exclude_list,$idx_list)=@_;

    save_regressions($this,$output_filename."_.rgrs");

    # make up list of output column names
    my $output_colnames=[];
    foreach my $colname (@{$this->{"colnames"}}) {
	my $found=0;
	foreach my $exclude (@{$exclude_list}) {
	    $found=1 if ($colname eq $exclude);		
	}
	push(@{$output_colnames},$colname) if (!$found);
    }

    printf STDERR "will export file %s containing the following column titles:\n%s\n",$output_filename,join(' ',@{$output_colnames});
    
    # proceed to output the resulting output file
    open(Q,">",$output_filename) || die "can't open output $output_filename\n";
    printf Q "rereferenced_ts5_data\n";
    printf Q "%s\n",join("\t",@{$output_colnames});
    foreach my $ix (@{$idx_list}) {
	my $output_str=[];
	foreach my $outcol (@{$output_colnames}) {
	    push(@{$output_str},sprintf("%s",$this->{$outcol}->[$ix]));
	}
	printf Q "%s\n",join(' ',@{$output_str});
    }
    close(Q);
}

sub append_diff {
    my ($this,$difflist,$diffname)=@_;
    my $diff=[];
    for (my $i=0;$i<$this->{"n_entry"};$i++) {
	$diff->[$i] = ($this->{$difflist->[0]}->[$i] - $this->{$difflist->[1]}->[$i]);
    }
    append_column($this,$diffname,$diff);
}

sub populate_ref_system {
    my ($this,$split_field_names,$ref_col_name,$sort_term)=@_;
    my ($rrf,$ms)=@{$split_field_names};
    my $verbose=0;
    my $ref_system=[];
    # generate sort_term choices
    my $reref=$this->{$rrf};
    my $reref_times=[];
#    if ($#{$reref} == -1) {
#	# if there are no rereference sets, use zeros
#	append_column($this,$ref_col_name,[(0)x$this->{"n_entry"}]);
#	return;
#    }
    foreach my $reref_ix (0..$#{$reref}) {
	push(@{$reref_times},$reref->[$reref_ix]->{"regr"}->{$sort_term});
    }
    # for each measurement ($rrf & $ms entries combined)
    for (my $ix=0;$ix<$this->{"n_entry"};$ix++) {
	my $st=$this->{$sort_term}->[$ix];
	# find the nearest neighbors in the sort_term from the rerefernce choices
	my $sort_term_ixlist=[sort {pow($reref_times->[$a]-$st,2) <=> 
					pow($reref_times->[$b]-$st,2)} (0..$#{$reref})];
	my @st_ix=@{$sort_term_ixlist}[0,1];
	my ($t0,$t1)=($reref_times->[$st_ix[0]],$reref_times->[$st_ix[1]]);
	my @weight=(($t1-$st)/($t1-$t0),($st-$t0)/($t1-$t0));
	my $evaluated_regression=[];

	foreach my $r_ix (0,1) {
	    # the regression
	    my $rgr=$reref->[$st_ix[$r_ix]]->{"regr"};
	    my $theta=$rgr->{"theta"};
	    my $regr_indep_axes=$rgr->{"regr_indep_axes"};
	    # the independent 
	    my $indep_vals=[];
	    foreach my $axis (@{$regr_indep_axes}) {
		push(@{$indep_vals},$this->{$axis}->[$ix]);
	    }
	    $evaluated_regression->[$r_ix]=0;
	    foreach my $axis_ix (0..$#{$theta}) {
		$evaluated_regression->[$r_ix] += $theta->[$axis_ix]*$indep_vals->[$axis_ix];
	    }
	    if ($verbose && ($this->{"label"}->[$ix] ne "REREF")) {
		printf STDERR ("%d: (regression evaluates to %g)\naxes: %s\ncoeffs: %s\nvals: %s\n",
			       $r_ix,
			       $evaluated_regression->[$r_ix],
			       join(' ',@{$regr_indep_axes}),
			       join(' ',@{$theta}),
			       join(' ',@{$indep_vals}));
	    }
	}
	my $interpolated_regression=0;
	foreach my $i (0,1) {
	    $interpolated_regression += $evaluated_regression->[$i]*$weight[$i];
	}

	if ($verbose && ($this->{"label"}->[$ix] ne "REREF")) {
	    printf STDERR ("rerefs nearest to sort_term %g are %g[%d]: %g ".
			   "(weight %g) and %g[%d]: %g (weight %g)\ninterpolated regression=%g\n",
			   $st,
			   $reref_times->[$sort_term_ixlist->[0]],
			   $sort_term_ixlist->[0],$evaluated_regression->[0],$weight[0],
			   $reref_times->[$sort_term_ixlist->[1]],
			   $sort_term_ixlist->[1],$evaluated_regression->[1],$weight[1],
			   $interpolated_regression);
	}
	$ref_system->[$ix]=$interpolated_regression;
    }
    append_column($this,$ref_col_name,$ref_system);
}

sub populate_reref_regressions {
    my ($this,$rrf,$regr_indep_axes,$regr_dep_axis,$sort_term)=@_;
    my $verbose=0;
    open(REG,">","reref_regressions.txt") || die;
    foreach my $reref_entry (@{$this->{$rrf}}) {
	my $st=0;
	my $n_st=0;
	my $rgressn=Statistics::Regression->new($regr_dep_axis,$regr_indep_axes);
	foreach my $ix (@{$reref_entry->{"ixs"}}) {
	    my %indep=();
	    my $dep;
	    foreach my $regr_indep (@{$regr_indep_axes}) {
		if ($verbose) {
		    printf STDERR "%s: %g ",$regr_indep,$this->{$regr_indep}->[$ix];
		}
		$indep{$regr_indep}=$this->{$regr_indep}->[$ix];
	    }
	    # and the dependent term
	    if ($verbose) {
		printf STDERR ("%s: %g sort %s: %g\n",
			       $regr_dep_axis,$this->{$regr_dep_axis}->[$ix],
			       $sort_term,$this->{$sort_term}->[$ix]);
	    }
	    
	    $st += $this->{$sort_term}->[$ix];
	    $n_st++;
	    $dep=$this->{$regr_dep_axis}->[$ix];
	    $rgressn->include($dep,[@indep{@{$regr_indep_axes}}]);
	}
# 	$rgressn->print();
	my $result_rgr=[$rgressn->theta()];

	if ($verbose) {
	    printf STDERR "theta: %s\n",join (' ',@{$result_rgr});
	    printf STDERR "ave(%s): %g\n\n",$sort_term,$st/$n_st;
	}
	
	$reref_entry->{"regr"}={};
	$reref_entry->{"regr"}->{"sort_term"}=$sort_term;
	$reref_entry->{"regr"}->{$sort_term}=$st/$n_st;
	$reref_entry->{"regr"}->{"regr_indep_axes"}=$regr_indep_axes;
	$reref_entry->{"regr"}->{"regr_dep_axis"}=$regr_dep_axis;
	$reref_entry->{"regr"}->{"theta"}=$result_rgr;

	if ($verbose) {
	    printf STDOUT "%g %s\n",$st/$n_st,join(' ',@{$result_rgr});
	}
	
	printf REG "%g %s\n",$st/$n_st,join(' ',@{$result_rgr});
    }
    close(REG);
}

sub split_reref_meas {
    my ($this,$split_field_names,$reref_label)=@_;
    # generate sub-arrays containing indices
    my ($rrf,$ms)=@{$split_field_names};
    foreach my $field ($rrf,$ms) {
	if (!defined($this->{$field})) {
	    $this->{$field}=[];
	} else {
	    printf STDERR "array $field already defined in $this.\nexiting..\n";
	    exit(1);
	}
    }

    # now pass through the data space and allocate array entries as needed.
    my $is_reref=0;
    my $this_reref=-1;
    my $last_aero_z=-1;
    for (my $ix=0;$ix<$this->{"n_entry"};$ix++) {
	if ($this->{"label"}->[$ix] eq $reref_label) {
	    if ($is_reref && ($this->{"aero_z"}->[$ix] == $last_aero_z)) { # still in sequence of reref values. append to existing list
	    } else {
		# append a new reref entry to $this->{"_reref"}
		$this_reref++;
		$this->{$rrf}->[$this_reref]={};
		$this->{$rrf}->[$this_reref]->{"ixs"}=[];
	    }
	    push(@{$this->{$rrf}->[$this_reref]->{"ixs"}},$ix);
	    $last_aero_z=$this->{"aero_z"}->[$ix];
	    $is_reref=1;
	} else {
	    $is_reref=0;
	    push(@{$this->{$ms}},$ix);
	}
    }
    return;
    # now check to see what reref looks like.
    printf STDERR "number of groups: %d\n",$#{$this->{$rrf}}-$[+1;
    for (my $grp_ix=0;$grp_ix<=$#{$this->{$rrf}};$grp_ix++) {
	my $this_group=$this->{$rrf}->[$grp_ix]->{"ixs"};
	printf STDERR "\tfrom %d to %d (\#entries: %d)\n",@{$this_group}[0,$#{$this_group}],$#{$this_group}-$[+1;
    }
    printf STDERR ".. and data field is %d long.\n",$#{$this->{$ms}}-$[+1;
}

sub append_sum {
    my ($this,$sumlist,$sum_name)=@_;
    my $zsum=[];
    for (my $ix=0;$ix<$this->{"n_entry"};$ix++) {
	$zsum->[$ix]=0;
	foreach my $arry (@{$sumlist}) {
	    $zsum->[$ix] += $this->{$arry}->[$ix];
	}
    }
    append_column($this,$sum_name,$zsum);
}

sub append_column {
    my ($this,$col_name,$col_data)=@_;
    if (!defined($this->{$col_name})) {
	$this->{$col_name}=$col_data;
	push(@{$this->{"colnames"}},$col_name);
    } else {
	printf STDERR "column $col_name already defined in $this.\nexiting..\n";
	exit(1);
    }
}

sub describe_contents {
    my ($this)=@_;
    printf STDERR ("currently have %d entries with column titles:\n%s\n",
		   $this->{"n_entry"},
		   join(' ',@{$this->{"colnames"}}));
}

sub read_scan_contents {
    my ($this,$gain)=@_;
    open(F,$this->{"filename"}) || die;
    my $strip_counter=0;
    $this->{"n_entry"}=0 if (!defined($this->{"n_entry"}));
    if (defined($gain)) {
	printf STDERR "will attempt to apply the following gain corrections:\n";
	my %gns=%{$gain->{"gain"}};
	while (my ($key,$val)= each %gns) {
	    printf STDERR "\t%s: %s\n",$key,$val;
	}
    }
    while (<F>) {
	chomp;
	if (/\#/) {
	    if (/TF/) {
		$this->{"TF"}={} if (!defined($this->{"TF"}));
		my ($key,$val)=($_ =~ /(\S+)\s*=\s*(\S+)/);
		$this->{"TF"}->{$key}=$val;
	    }
	    # nominally should expect a transform specification (TF)
	    # to contain keyword/values for X0, Y0, theta which should be traced to metro_scan.perl
	    next;
	}

	next if (/FFF/);
	next if (/SELFCAL/); # dont include selfcal in data

	$this->{"hdr"}=$_ if ($strip_counter==0); # probably won't use it, save it for now
	if ($strip_counter==1) {
	    $this->{"colnames"}=[split('\t')];
	    foreach my $colname (@{$this->{"colnames"}}) {
		$this->{$colname} = [];
	    }
	}
	if ($strip_counter>1) { # read data content
	    my @contents = split(' ');
	    foreach my $ix (0..$#contents) {
		my $cn=$this->{"colnames"}->[$ix];
		if (defined($gain) && defined($gain->{"gain"}->{$cn})) {
		    push(@{$this->{$cn}},$contents[$ix]*$gain->{"gain"}->{$cn});
		} else {
		    push(@{$this->{$cn}},$contents[$ix]);
		}
	    }
	    $this->{"n_entry"}++;
	}
	$strip_counter++;
    }
    close(F);
}
