#!/usr/bin/perl
use warnings;
use strict;
use POSIX;
use PGPLOT;
use Cwd;
use File::Basename;
use Getopt::Long;
use Astro::FITS::CFITSIO qw( :constants );

my $usage=
    "\nusage:\n".
    "$0 [args]\n".
    "\n[args] are any combination of:\n".
    "\t[ --warm <warm_input1.tnt> <warm_input1 temperature>\n".
    "\t [--warm <warm_input2.tnt> <warm_input2 temperature>]\n".
    "\t  .....\n".
    "\t [--warm <warm_inputN.tnt> <warm_inputN temperature>]]\n".
    "\t[ --cold <cold_input1.tnt> <cold_input1 temperature>\n".
    "\t [--cold <cold_input2.tnt> <cold_input2 temperature>]\n".
    "\t  .....\n".
    "\t [--cold <cold_inputM.tnt> <cold_inputM temperature>]]\n".
    "\t[--compute_cold_minus_warm]\n".
    "\t[ --set <dataset_input1.tnt> <dataset1_identifier>\n".
    "\t [--set <dataset_input2.tnt> <dataset2_identifier>]\n".
    "\t  .....\n".
    "\t [--set <dataset_inputR.tnt> <datasetR_identifier>]]\n".
    "\t[--compute_set_differences]\n".
    "\t[--help]\n\n".
    "$0 will read in as many <warm_input.tnt> and\n".
    "<cold_input.tnt> files as are named, and will generate\n".
    "results for raft_imageheight, raft_flatness and sensor_flatness\n".
    "in the forms of histograms, quantiles and maps.\n\n".
    "If the switch --compute_cold_minus_warm is set, MxN pairs of scans\n".
    "will be subtracted, cold minus warm, and comparable analysis is\n".
    "performed on those difference maps.\n\n".
    "All <*input?.tnt> files may be standard output files created by \n".
    "slac_ts5_parse_scan.perl. This will ensure presence of expected \n".
    "column names.\n\n";

my @warm_opts;
my @cold_opts;
my @set_opts;
my $warm_temperatures;
my $cold_temperatures;
my $temperatures;
my $compute_cold_minus_warm=0;
my $compute_set_differences=0;
my $help=0;

GetOptions("warm=s{2}" => \@warm_opts,
	   "cold=s{2}" => \@cold_opts,
	   "set=s{2}"  => \@set_opts,
	   "compute_cold_minus_warm" => \$compute_cold_minus_warm,
	   "compute_set_differences" => \$compute_set_differences,
	   "help"      => \$help) || ($help=1);

if ($help) {
    printf STDERR "%s",$usage;
    exit(1);
}

$warm_temperatures={@warm_opts};
$cold_temperatures={@cold_opts};
$temperatures={@warm_opts,@cold_opts};
my $sets={@set_opts};

# this is done to maintain order in difference calculations (not necessary for "cold_minus_warm")
my @ordered_set_inputs=();
for (my $iix=0;$iix<=$#set_opts;$iix+=2) {
    push(@ordered_set_inputs,$set_opts[$iix]);
}

my $infiles1=[keys %{$temperatures}];
my $infiles2=[keys %{$sets}];

my $output_graphics_file_list;

my $report_axes=["TS5_CMM_ballplane_ref",
		 "TS5_CMM_ballplane_ref_rr",
		 "TS5_CMM_ballplane_ref_pwl_rr"];

my $titles=["raft imageheight","raft flatness","sensor flatness"];

# $report_axes=["TS5_CMM_ballplane_ref_rr"];
# $titles=["raft flatness"];

#$report_axes=["TS5_CMM_ballplane_ref_pwl_rr"];
#$titles=["sensor flatness"];

#$report_axes=["key_zsum_ref_rr"];
#$titles=["reref zsum"];

my $tnt={};
my $device="/xserve";
$device="/cps";

pgbegin(0,$device,1,1);

my $xax="raft_x";
my $yax="raft_y";

foreach my $infile (@{$infiles1},@{$infiles2}) {
    $tnt->{$infile}=read_tnt($infile);
    append_edge_distances($tnt->{$infile},[$xax,$yax],"edgedist"); # specific to raft style datasets
}

my $status=0;
my $fitsfile_out;

if (defined($ENV{"LCATR_UNIT_ID"})) {
    $fitsfile_out=sprintf("%s_ts5_maps.fits",$ENV{"LCATR_UNIT_ID"});
} else {
    $fitsfile_out="ts5_maps.fits";
}

my $fptr=Astro::FITS::CFITSIO::create_file("!".$fitsfile_out,$status);
printf "status=$status\n" if ($status);
$fptr->create_img(DOUBLE_IMG,2,[0,0],$status);
printf "status=$status\n" if ($status);
my $edge_threshold;

foreach my $zax_ix (0..$#{$report_axes}) {
    my $zax=$report_axes->[$zax_ix];
    foreach my $infiles ($infiles1,$infiles2) {
	
	foreach my $infile (@{$infiles}) {
	    #    printf "headings are: %s\n",join(" ",@{$tnt->{$infile}->{"headings"}});
	    my $cond;
	    if ($infiles eq $infiles1) {
		$cond=sprintf("(T=%s)",$temperatures->{$infile});
	    } else {
		$cond=sprintf("(%s)",$sets->{$infile});
	    }

	    foreach $edge_threshold (0.5) {

		$tnt->{$infile}->{"hist"}=make_histogram(
		    {("data"         => $tnt->{$infile},
		      "axis"         => $zax,
		      "max_binwidth" => 0.00015,
		      "edgethresh"   => $edge_threshold,
		      "nbin"         => 200,
		      "title"        => sprintf("%s distribution %s",
						$titles->[$zax_ix],
						$cond)    )});
		
		draw_histogram($tnt->{$infile}->{"hist"});
		record_filename([$infile." edgethresh=".$edge_threshold]);
		{
		    my $title=$titles->[$zax_ix];
		    $title =~ tr/\ /-/;
		    my $output_root=join('_',$infile,"et".$edge_threshold,$title,"histogram");
		    push(@{$output_graphics_file_list},$output_root);
		    output_histogram_results($output_root,$tnt->{$infile}->{"hist"}->{"results"});
		}
		
		my $qlvls=$tnt->{$infile}->{"hist"}->{"qlvls"};
		my $lmts=[$tnt->{$infile}->{"hist"}->{"quant"}->{$qlvls->[2]},
			  $tnt->{$infile}->{"hist"}->{"quant"}->{$qlvls->[6]}];
		
		draw_falsecolor_map({("data" => $tnt->{$infile},
				      "xax" => $xax,"yax" => $yax,"zax" => $zax,
				      "title" => sprintf("%s map %s",$titles->[$zax_ix],$cond),
				      "edgethresh" => $edge_threshold,
				      "limits" => $lmts,
				      "fitsfile" => $fptr)});
		record_filename([$infile."_edgethresh=".$edge_threshold]);
		{
		    my $title=$titles->[$zax_ix];
		    $title =~ tr/\ /-/;
		    push(@{$output_graphics_file_list},
			 join('_',$infile,"et".$edge_threshold,$title,"map"));
		}
	    }
	}
    }

    my $differences=[];

    if ($compute_cold_minus_warm) {
	foreach my $cold (keys %{$cold_temperatures}) {
	    foreach my $warm (keys %{$warm_temperatures}) {
		push(@{$differences},{("set1" => $cold,
				       "set2" => $warm,,
				       "key"  => $zax." : ".$cold."_diff_".$warm,
				       "hist_comment" => 
				       sprintf("%s difference distribution (T: %s vs. %s)",
					       $titles->[$zax_ix],
					       @{$temperatures}{$cold,$warm}),
				       "map_comment" => 
				       sprintf("%s difference map (T: %s vs. %s)",
					       $titles->[$zax_ix],
					       @{$temperatures}{$cold,$warm})
				       )});
	    }
	}
    }

    if ($compute_set_differences) {
	my @s_sets=@ordered_set_inputs;
	foreach my $s1_ix (0..$#s_sets-1) {
	    foreach my $s2_ix (1..$#s_sets) {
		my ($set1,$set2) = @s_sets[$s1_ix,$s2_ix];
		push(@{$differences},{("set1" => $set1,
				       "set2" => $set2,
				       "key"  => $zax." : ".$set1."_diff_".$set2,
				       "hist_comment" => 
				       sprintf("%s difference distribution (%s minus %s)",
					       $titles->[$zax_ix],@{$sets}{$set1,$set2}),
				       "map_comment"=> sprintf("%s difference map (%s minus %s)",
							       $titles->[$zax_ix],
							       @{$sets}{$set1,$set2}))});
	    }
	}
    }

    foreach my $diff_ix (0..$#{$differences}) {
	my ($set1,$set2)=@{$differences->[$diff_ix]}{"set1","set2"};
	# make up a difference map.
	my $diff_maps=[];
	my $diff_hist;
	# allocate new difference arrays that will be stored as 
	# $tnt->{$infiles1->[0]."_diff_".$infiles1->[1]}
	my $key=$differences->[$diff_ix]->{"key"};
	my $dat;
	if (!defined($tnt->{$key})) {
	    $dat={};
	    $tnt->{$key}={};
	    $tnt->{$key}->{"dat"}=$dat;
	    $tnt->{$key}->{"headings"}=[];
	    $tnt->{$key}->{"ndat"}=0;
	    $tnt->{$key}->{"nxs"}=0;
	    $tnt->{$key}->{"ixs"}={};
	    foreach my $ax ($xax,$yax) {
		$dat->{$ax}=[];
		push(@{$tnt->{$key}->{"headings"}},$ax);
		my $this_ix=$tnt->{$key}->{"nxs"};
		$tnt->{$key}->{"ixs"}->{$ax} = $this_ix;
		$tnt->{$key}->{"nxs"}++;
	    }
	}
	$dat->{$zax."_diff"}=[];
	push(@{$tnt->{$key}->{"headings"}},$zax."_diff");
	$tnt->{$key}->{"ixs"}->{$zax."_diff"} = $tnt->{$key}->{"nxs"};
	$tnt->{$key}->{"nxs"}++;
	for (my $k=0;$k<9;$k++) {
	    
	    my ($map1,$map2)=($tnt->{$set1}->{"maps"}->{$zax}->[$k],
			      $tnt->{$set2}->{"maps"}->{$zax}->[$k]);
	    my @tf=@{$map1->{"transform"}};
	    my ($tnx,$tny)=@{$map1->{"dim"}};
	    my ($value,$samples,$vals)=([],[],[]);
	    for (my $j=0;$j<$tny;$j++) {
		$value->[$j]=[];
		$samples->[$j]=[];
		for (my $i=0;$i<$tnx;$i++) {
		    $samples->[$j]->[$i] = ($map1->{"samples"}->[$j]->[$i]*
					    $map2->{"samples"}->[$j]->[$i]);
		    $value->[$j]->[$i] = ($map1->{"value"}->[$j]->[$i]-
					  $map2->{"value"}->[$j]->[$i]);
		    if ($samples->[$j]->[$i]!=0) {
			push(@{$vals},$value->[$j]->[$i]);

			push(@{$tnt->{$key}->{$xax}},
			     $tf[0] + $tf[1]*($i+1) + $tf[2]*($j+1));
			push(@{$tnt->{$key}->{$yax}},
			     $tf[3] + $tf[4]*($i+1) + $tf[5]*($j+1));
			push(@{$tnt->{$key}->{$zax."_diff"}},
			     $value->[$j]->[$i]);
			$tnt->{$key}->{"ndat"}++;
		    }
		}
	    }
	    my @zv=sort {$a<=>$b} @{$vals};
	    my $map={("value"   => $value,
		      "samples" => $samples,
		      "diffs"   => $vals,
		      "ndim"    => 2,
		      "dim"     => [$tnx,$tny],
		      "zsc"     => [@zv[0,$#zv]],
		      "transform" => $map1->{"transform"})};
	    $diff_maps->[$k] = $map;
	}
	# now establish llim & ulim.
	$tnt->{$key}->{"llim"}=[];
	$tnt->{$key}->{"ulim"}=[];
	for (my $ix=0;$ix<$tnt->{$key}->{"nxs"};$ix++) {
	    my @ary=(sort {$a<=>$b} 
		     @{$tnt->{$key}->{$tnt->{$key}->{"headings"}->[$ix]}});
	    ($tnt->{$key}->{"llim"}->[$ix],
	     $tnt->{$key}->{"ulim"}->[$ix])=@ary[0,$#ary];
	    #    printf "limits for axis %d: (%g,%g)\n",$ix,@ary[0,$#ary];
	}
	# try out the 2d hist sampled values.. generated
	# printf "zax = $zax.. headings are %s\n",join(' ',@{$tnt->{$key}->{"headings"}});
	$tnt->{$key}->{"hist"}=
	    make_histogram({("data"  => $tnt->{$key},
			     "axis"  => $zax."_diff",
			     "max_binwidth" => 0.0002,
			     "edgethresh" => 0,
			     "nbin"  => 200,
			     "title" => $differences->[$diff_ix]->{"hist_comment"})});
	draw_histogram($tnt->{$key}->{"hist"});
	record_filename([$set1,$set2]);
	{
	    my $title=$titles->[$zax_ix];
	    $title =~ tr/\ /-/;
	    push(@{$output_graphics_file_list},
		 dirname($set1)."/".join('_',basename($set1),"diff",basename($set2),$title,"histogram"));
	}

	my $qlvls=$tnt->{$key}->{"hist"}->{"qlvls"};
	my $lmts=[$tnt->{$key}->{"hist"}->{"quant"}->{$qlvls->[1]},
		  $tnt->{$key}->{"hist"}->{"quant"}->{$qlvls->[7]}];
	
	# maps are ready to go, but need to determine common scaling first
	my ($zlvals,$zuvals)=([],[]);
	for (my $k=0;$k<9;$k++) {
	    push(@{$diff_hist},@{$diff_maps->[$k]->{"diffs"}});
	    push(@{$zlvals},$diff_maps->[$k]->{"zsc"}->[0]);
	    push(@{$zuvals},$diff_maps->[$k]->{"zsc"}->[1]);
	}

	# the false color plot
	my $llim=$tnt->{$set1}->{"llim"};
	my $ulim=$tnt->{$set1}->{"ulim"};
	my $xix=$tnt->{$set1}->{"ixs"}->{$xax};
	my $yix=$tnt->{$set1}->{"ixs"}->{$yax};
	my $xsp=0.03*($tnt->{$set1}->{"ulim"}->[$xix]-
		      $tnt->{$set1}->{"llim"}->[$xix]);
	my $ysp=0.03*($tnt->{$set1}->{"ulim"}->[$yix]-
		      $tnt->{$set1}->{"llim"}->[$yix]);
	pgenv($llim->[$xix]-$xsp,$ulim->[$xix]+$xsp,
	      $llim->[$yix]-$ysp,$ulim->[$yix]+$ysp,1,0);
	pglabel($tnt->{$set1}->{"headings"}->[$xix]." [mm]",
		$tnt->{$set1}->{"headings"}->[$yix]." [mm]",
		$differences->[$diff_ix]->{"map_comment"});
	my ($zu,$zl)=($diff_maps->[0]->{"zsc"}->[1],
		      $diff_maps->[0]->{"zsc"}->[0]);
	($zu,$zl)=($zu-0.25*($zu-$zl),$zl+0.25*($zu-$zl));
	($zu,$zl)=(+10e-3,-10e-3);
	($zl,$zu)=@{$lmts};
	for (my $i=0;$i<3;$i++) {
	    for (my $j=0;$j<3;$j++) {
		my $k=3*$j+$i;
		@{$diff_maps->[$k]->{"zsc"}}=($zl,$zu);
		pgimag_by_parts($diff_maps->[$k]);
	    }
	}
	record_filename([$set1,$set2]);
	pgwedg("RI",1,3,$zu,$zl,$zax." difference [mm]");
	pgiden();
	{
	    my $title=$titles->[$zax_ix];
	    $title =~ tr/\ /-/;
	    push(@{$output_graphics_file_list},
		 dirname($set1)."/".join('_',basename($set1),"diff",basename($set2),$title,"map"));
	}
    }
}

pgend();

exit if ($#{$output_graphics_file_list}<0);
printf "outputs: %s\n",join(' ',@{$output_graphics_file_list});
# convert pgplot.ps into pdf and repeatedly run convert..
if ($device eq "/cps") {
    `ps2pdf pgplot.ps`;
    foreach my $ix (0..$#{$output_graphics_file_list}) {
	my $cmd;
#	foreach my $suffix ("pdf","png") {
	foreach my $suffix ("png") {
	    $cmd=sprintf("convert -density 150 pgplot.pdf['%d'] %s.%s",
			 $ix,$output_graphics_file_list->[$ix],$suffix);
	    printf "converting pgplot.pdf[%d] as %s.%s\n",$ix,$output_graphics_file_list->[$ix],$suffix;
	    `$cmd`;
	    { # move output file to current directory, jh needs to find them here.
		my $of=sprintf("%s.%s .",$output_graphics_file_list->[$ix],$suffix);
		if (dirname($of) ne ".") {
		    my $cmd=sprintf("mv %s.%s .",$of,$suffix);
		    printf "moving %s.%s to current directory.\n",$ix,$output_graphics_file_list->[$ix],$suffix;
		    `$cmd`;
		}
	    }
	}
    }
    unlink glob "pgplot*";
}

# now convert pgpplot.ps into a pdf, then extract into individual png files
# and erase ps & pdf files.


sub read_tnt {
    my ($input)=@_;
    my $dat={};
    my $filter={"raft_x" => [-70,70]};
    open(F,"<",$input) || die "can't load input file ".$input;
    my $line=<F>;
    $line=<F>;
    chomp $line;
    my $hdr=[split("\t",$line)];
    my $hd;
    my $kix;
    foreach $hd (@{$hdr}) {
	$dat->{$hd}=[];
    }
    $dat->{"ndat"}=0;

    foreach my $j (0..$#{$hdr}) {
	foreach my $k ( keys %{$filter} ) {
	    $kix=$j if ($hdr->[$j] eq $k);
	}
    }

    while ($line=<F>) {
	chomp $line;
	my @contents=split(' ',$line);
	next if (defined($kix) && 
		 (($contents[$kix]-$filter->{$hdr->[$kix]}->[0])*
		  ($filter->{$hdr->[$kix]}->[1]-$contents[$kix])<0));
	foreach my $i (0..$#contents) {
	    push(@{$dat->{$hdr->[$i]}},$contents[$i]);
	}
	$dat->{"ndat"}++;
    }
    close(F);
    $dat->{"llim"}=[];
    $dat->{"ulim"}=[];
    $dat->{"ixs"}={};
    foreach my $i (0..$#{$hdr}) {
	my @arry=sort {$a<=>$b} @{$dat->{$hdr->[$i]}};
	$dat->{"llim"}->[$i]=$arry[0];
	$dat->{"ulim"}->[$i]=$arry[$#arry];
	$dat->{"ixs"}->{$hdr->[$i]}=$i;
	#	printf STDERR "for %s (min,max)=(%g,%g)\n",$hdr->[$i],$dat->{"llim"}->[$i],$dat->{"ulim"}->[$i];
    }
    $dat->{"headings"}=$hdr;
    $dat;
}

sub append_edge_distances {
    my ($tnt,$cn,$edgedist)=@_;
    # determine nominal centroid & limits for each sensor on the raft
    my ($xn,$yn)=@{$cn};
    my $llim={($xn => $tnt->{"llim"}->[$tnt->{"ixs"}->{$xn}],
	       $yn => $tnt->{"llim"}->[$tnt->{"ixs"}->{$yn}])};
    my $ulim={($xn => $tnt->{"ulim"}->[$tnt->{"ixs"}->{$xn}],
	       $yn => $tnt->{"ulim"}->[$tnt->{"ixs"}->{$yn}])};
    my $wid={($xn => ($ulim->{$xn} - $llim->{$xn})/3.0,
	      $yn => ($ulim->{$yn} - $llim->{$yn})/3.0)};
    my $rcen={($xn => ($ulim->{$xn} + $llim->{$xn})/2.0,
	       $yn => ($ulim->{$yn} + $llim->{$yn})/2.0)};
    my $cen={};
    for (my $h=0;$h<3;$h++) {
	for (my $v=0;$v<3;$v++) {
	    $cen->{$h,$v}={($xn => $rcen->{$xn}+($h-1)*$wid->{$xn},
			    $yn => $rcen->{$yn}+($v-1)*$wid->{$yn})};
	}
    }
    # adjust boundaries (skip over gaps)

    # make up a new array handle and column name that indicates the distance to 
    # nearest edge. this will be used for filtering.
    my ($xlst,$ylst)=({},{});
    my $ownership=[];
    for (my $i=0;$i<$tnt->{"ndat"};$i++) {
	my ($x,$y)=($tnt->{$xn}->[$i],$tnt->{$yn}->[$i]);
	# which sensor does this belong to?
	my ($h,$v)=(floor(($x-$rcen->{$xn})/$wid->{$xn}+1.5),
		    floor(($y-$rcen->{$yn})/$wid->{$yn}+1.5));
	$xlst->{$h,$v}=[] if (!defined($xlst->{$h,$v}));
	$ylst->{$h,$v}=[] if (!defined($ylst->{$h,$v}));
	push(@{$xlst->{$h,$v}},$x);
	push(@{$ylst->{$h,$v}},$y);
	$ownership->[$i]=join($;,$h,$v);
    }
    # and find limits:
    my ($xll,$xul,$yll,$yul)=({},{},{},{});
    for (my $h=0;$h<3;$h++) {
	for (my $v=0;$v<3;$v++) {
	    next if (!defined($xlst->{$h,$v}));
	    my @list;
	    @list=@{$xlst->{$h,$v}};
	    @list = sort {$a<=>$b} @list;
	    ($xll->{$h,$v},$xul->{$h,$v})=@list[0,$#list];
	    @list=@{$ylst->{$h,$v}};
	    @list = sort {$a<=>$b} @list;
	    ($yll->{$h,$v},$yul->{$h,$v})=@list[0,$#list];
	}
    }

    # now assign nearest distance to border for each sensor.
    my $edge_distance=[];
    my $edge_distance_name=$edgedist;

    my ($xa,$ya)=($tnt->{$xn},$tnt->{$yn});

    for (my $i=0;$i<$tnt->{"ndat"};$i++) {
	my ($x,$y)=($xa->[$i],$ya->[$i]);
	my $o=$ownership->[$i];
	if (!defined($xll->{$o}) || !defined($xul->{$o}) ||
	    !defined($yll->{$o}) || !defined($yul->{$o})) {
	    $edge_distance->[$i]=0;
	} else {
	    $edge_distance->[$i]=(sort {$a<=>$b} (sqrt(pow($xll->{$o}-$x,2)),
						  sqrt(pow($xul->{$o}-$x,2)),
						  sqrt(pow($yll->{$o}-$y,2)),
						  sqrt(pow($yul->{$o}-$y,2))))[0];
	}
    }
    # append to $tnt
    push(@{$tnt->{"headings"}},$edge_distance_name);
    $tnt->{$edge_distance_name}=$edge_distance;
}

sub draw_falsecolor_map {
    my ($specs)=@_;
    my ($tnt,$xax,$yax,$zax,$title,$limits,$edgethresh,$fitsfile)=
	($specs->{"data"},$specs->{"xax"},
	 $specs->{"yax"},$specs->{"zax"},
	 $specs->{"title"},
	 $specs->{"limits"},
	 $specs->{"edgethresh"},
	 $specs->{"fitsfile"});

    my ($xix,$yix,$zix)=($tnt->{"ixs"}->{$xax},
			 $tnt->{"ixs"}->{$yax},
			 $tnt->{"ixs"}->{$zax});

    # turn the sparse array into a 2D array for plotting purposes. also keep nsamples
    my $imh=[];
    my ($nx,$ny)=(200,200);
    my ($xof,$yof,$xbw,$ybw)=($tnt->{"llim"}->[$xix],
			      $tnt->{"llim"}->[$yix],
			      ($tnt->{"ulim"}->[$xix]-$tnt->{"llim"}->[$xix])/($nx*1.0),
			      ($tnt->{"ulim"}->[$yix]-$tnt->{"llim"}->[$yix])/($ny*1.0));
    my ($xbin,$ybin);
    my ($xa,$ya,$za)=($tnt->{$xax},$tnt->{$yax},$tnt->{$zax});
    my $fh=[];
    my $zh=[];
    my $ns=[];

    for (my $j=0;$j<$ny;$j++) {
	$zh->[$j]=[];
	$ns->[$j]=[];
	$fh->[$j]=[];
	for (my $i=0;$i<$nx;$i++) {
	    $fh->[$j]->[$i]=0;
	    $zh->[$j]->[$i]=0;
	    $ns->[$j]->[$i]=0;
	}
    }

    for (my $i=0;$i<$tnt->{"ndat"};$i++) {
	next if ($tnt->{"edgedist"}->[$i] < $edgethresh);
	$xbin=floor(($xa->[$i]-$xof)/$xbw);
	$ybin=floor(($ya->[$i]-$yof)/$ybw);
	$ns->[$ybin]->[$xbin] += 1;
	$zh->[$ybin]->[$xbin] += $za->[$i];
    }

    # parasitically determine the limits of the ratio array
    my @zv=();
    for (my $j=0;$j<$ny;$j++) {
	for (my $i=0;$i<$nx;$i++) {
	    if ($ns->[$j]->[$i]<=0) {
		$fh->[$j]->[$i]=-99;
	    } else {
		$zh->[$j]->[$i] /= (1.0*$ns->[$j]->[$i]);
		$fh->[$j]->[$i] = $zh->[$j]->[$i];
		push(@zv,$zh->[$j]->[$i]);
	    }
	}
    }

    if (defined($fitsfile)) {
	my $status=0;
	$fptr->create_img(DOUBLE_IMG,2,[$ny,$nx],$status);
	printf "status=$status\n" if ($status);

	$fptr->write_key(TSTRING,"EXTNAME",$title,"",$status);
	$fptr->write_key(TSTRING,"PIXVAL",$zax,$title,$status);
	$fptr->write_key_unit("PIXVAL","mm",$status);

	$fptr->write_key(TDOUBLE,"LTM1_1",-1,"",$status);
	$fptr->write_key(TDOUBLE,"LTM1_2", 0,"",$status);
	$fptr->write_key(TDOUBLE,"LTM2_1", 0,"",$status);
	$fptr->write_key(TDOUBLE,"LTM2_2",+1,"",$status);

	$fptr->write_key(TDOUBLE,"LTV1",(1+$nx)/2.0,"",$status);
	$fptr->write_key_unit("LTV1","bin at raft center",$status);
	$fptr->write_key(TDOUBLE,"LTV2",(1+$ny)/2.0,"",$status);
	$fptr->write_key_unit("LTV2","bin at raft center",$status);

	$fptr->write_key(TDOUBLE,"DTM1_1",$xbw,"",$status);
	$fptr->write_key(TDOUBLE,"DTM1_2",0,"",$status);
	$fptr->write_key(TDOUBLE,"DTM2_1",0,"",$status);
	$fptr->write_key(TDOUBLE,"DTM2_2",$ybw,"",$status);

	$fptr->write_key(TDOUBLE,"DTV1",0,"",$status);
	$fptr->write_key_unit("DTV1","mm from raft center, CCS_x",$status);
	$fptr->write_key(TDOUBLE,"DTV2",0,"",$status);
	$fptr->write_key_unit("DTV2","mm from raft center, CCS_y",$status);
	
	printf "status=$status\n" if ($status);
	my $null=-99;
	for (my $row=0;$row<$ny;$row++) {
	    $fptr->write_pixnull(TDOUBLE,[1,$row+1],$nx,$fh->[$row],$null,$status);
	    printf "status=$status\n" if ($status);
	}
    }

    @zv = sort {$a<=>$b} @zv;


    my $xsp=0.03*($tnt->{"ulim"}->[$xix]-$tnt->{"llim"}->[$xix]);
    my $ysp=0.03*($tnt->{"ulim"}->[$yix]-$tnt->{"llim"}->[$yix]);

    # pgslw(3.0);
    pgscf(2);
    pgsch(1.2);
    pgenv($tnt->{"llim"}->[$xix]-$xsp,$tnt->{"ulim"}->[$xix]+$xsp,
	  $tnt->{"llim"}->[$yix]-$ysp,$tnt->{"ulim"}->[$yix]+$ysp,1,0);

    pglabel($tnt->{"headings"}->[$xix]." [mm]",
	    $tnt->{"headings"}->[$yix]." [mm]",
	    $title);

    my ($zl,$zu)=@zv[0,$#zv];
    #    ($zl,$zu)=(-10e-3,10e-3);
    #	    ($zl,$zu)=($zl+0.45*($zu-$zl),$zu-0.3*($zu-$zl));
    ($zl,$zu)=@{$limits};
    my ($cimin,$cimax)=(16.0,99.0);
    for (my $ci=$cimin;$ci<=$cimax;$ci++) {
	my $f=($cimax-$ci)/($cimax-$cimin);
	my ($r,$g,$b)=(1.0*exp(-pow(($f-1.00)/(sqrt(2)*0.40),2)),
		       0.9*exp(-pow(($f-0.50)/(sqrt(2)*0.15),2)),
		       1.0*exp(-pow(($f-0.30)/(sqrt(2)*0.20),2)));
	($r,$g,$b)=($f,0,1-$f);
	pgscr($ci,$r,$g,$b);
    }
    pgscir($cimin,$cimax);
    my $which=2;
    if ($which == 0) {
	pgimag($zh,$nx,$ny,1,$nx/2,1,$ny,$zu,$zl,
	       [$xof-0.5*$xbw,$xbw,0,$yof-0.5*$ybw,0,$ybw]);
	pgimag($zh,$nx,$ny,$nx/2,$nx,1,$ny,$zu,$zl,
	       [$xof-0.5*$xbw,$xbw,0,$yof-0.5*$ybw,0,$ybw]);
    } elsif ($which == 1) {
	# point by point..
	for (my $j=0;$j<$tnt->{"ndat"};$j++) {
	    next if ($tnt->{"edgedist"}->[$j] < $edgethresh);
	    pgimag([[$za->[$j]]],1,1,1,1,1,1,$zu,$zl,
		   [$xa->[$j]-0.5*$xbw,$xbw,0,$ya->[$j]-0.5*$ybw,0,$ybw]);
	}
    } elsif ($which == 2) {
	# try to make a map for each sensor.
	# pass through the list 9 times, each time make up a 2d hist sub-array
	# to plot.
	for (my $h=0;$h<3;$h++) {
	    for (my $v=0;$v<3;$v++) {
		my ($xw,$yw)=(($tnt->{"ulim"}->[$xix]-$tnt->{"llim"}->[$xix])/3.0,
			      ($tnt->{"ulim"}->[$yix]-$tnt->{"llim"}->[$yix])/3.0);
		my ($xc,$yc)=((($tnt->{"llim"}->[$xix]+$tnt->{"ulim"}->[$xix])/2.0
			       +($h-1)*$xw),
			      (($tnt->{"llim"}->[$yix]+$tnt->{"ulim"}->[$yix])/2.0
			       +($v-1)*$yw));
		my ($xl,$xu,$yl,$yu)=($xc-0.5*$xw,$xc+0.5*$xw,
				      $yc-0.5*$yw,$yc+0.5*$yw);
		my ($tzh,$tns)=([],[]);
		my ($tnx,$tny)=(60,60);
		for (my $j=0;$j<$tny;$j++) {
		    $tzh->[$j]=[];
		    $tns->[$j]=[];
		    for (my $i=0;$i<$tnx;$i++) {
			$tzh->[$j]->[$i]=0;
			$tns->[$j]->[$i]=0;
		    }
		}
		# determine max & min
		my ($xlist,$ylist,$zlist)=([],[],[]);
		for (my $i=0;$i<$tnt->{"ndat"};$i++) {
		    next if ((($xa->[$i]-$xl)*($xu-$xa->[$i])<0) ||
			     (($ya->[$i]-$yl)*($yu-$ya->[$i])<0));
		    next if ($tnt->{"edgedist"}->[$i] < $edgethresh);
		    push(@{$xlist},$xa->[$i]);
		    push(@{$ylist},$ya->[$i]);
		    push(@{$zlist},$za->[$i]);
		}
		my @arr;
		@arr=sort {$a<=>$b} @{$xlist};		($xl,$xu)=@arr[0,$#arr];
		@arr=sort {$a<=>$b} @{$ylist};		($yl,$yu)=@arr[0,$#arr];

		($xof,$yof)=($xl,$yl);
		($xbw,$ybw)=(($xu-$xl)/(1.0*$tnx),($yu-$yl)/(1.0*$tny));
		
		foreach my $i (0..$#{$xlist}) {
		    $xbin=floor(($xlist->[$i]-$xof)/$xbw);
		    $ybin=floor(($ylist->[$i]-$yof)/$ybw);
		    $tns->[$ybin]->[$xbin] += 1;
		    $tzh->[$ybin]->[$xbin] += $zlist->[$i];
		}
		for (my $j=0;$j<$tny;$j++) {
		    for (my $i=0;$i<$tnx;$i++) {
			if ($tns->[$j]->[$i]>0) {
			    $tzh->[$j]->[$i] /= (1.0*$tns->[$j]->[$i]);
			}
		    }
		}
		# store the data in the tnt structure, indexed by the column name
		$tnt->{"maps"}={} if (!defined($tnt->{"maps"}));
		$tnt->{"maps"}->{$zax}=[] if (!defined($tnt->{"maps"}->{$zax}));

		my $map={("value"  => $tzh,
			  "samples"=> $tns,
			  "ndim"     => 2,
			  "dim"      => [$tnx,$tny],
			  "zsc"      => [$zl,$zu],
			  "transform"=> [$xof-0.5*$xbw,$xbw,0,
					 $yof-0.5*$ybw,0,$ybw])};
		# store
		$tnt->{"maps"}->{$zax}->[$v*3+$h] = $map;
		# now plot.
		my $choice=2;
		if ($choice == 0) {
		    pgimag($map->{"value"},
			   $map->{"dim"}->[0],$map->{"dim"}->[1],
			   1,$map->{"dim"}->[0],1,$map->{"dim"}->[1],
			   $map->{"zsc"}->[1],$map->{"zsc"}->[0],$map->{"transform"});
		} elsif ($choice == 1) {
		    # do this one line at a time
		    for (my $yi=0;$yi<$map->{"dim"}->[1];$yi++) {
			pgimag($map->{"value"},
			       $map->{"dim"}->[0],
			       $map->{"dim"}->[1],
			       1,$map->{"dim"}->[0],
			       $yi+1,$yi+1,
			       $map->{"zsc"}->[1],
			       $map->{"zsc"}->[0],
			       $map->{"transform"});
		    }
		} elsif ($choice == 2) {
		    pgimag_by_parts($map);
		} else {
		    # do nothing.
		}
	    }
	}
    }
    pgwedg("RI",1,3,$zu,$zl,$zax." [mm]");
    #    my ($icilo,$icihi);
    #    pgqcir($icilo,$icihi);
    #    printf "icilo %g icihi %g\n",$icilo,$icihi;
    pgiden();
    
}

sub make_histogram {
    my ($specs)=@_;
    my ($tnt,$axis,$nbin,$maxbinwid,$edgethresh,$title)=($specs->{"data"},$specs->{"axis"},$specs->{"nbin"},
							 $specs->{"max_binwidth"},$specs->{"edgethresh"},$specs->{"title"});

    my @zv=@{$tnt->{$axis}};
    
    my $use_ndat;
    { # do some spatial filtering based on edges
	my @tmpzv=();
	for (my $i=0;$i<$tnt->{"ndat"};$i++) {
	    next if ($tnt->{"edgedist"}->[$i]<$edgethresh); # or whatever threshold
	    push(@tmpzv,$tnt->{$axis}->[$i]);
	}
	@zv=@tmpzv;
	$use_ndat=$#zv-$[+1;
    }

    @zv = sort {$a<=>$b} @zv;
    # extract the quantiles here before @zv is modified below
    my @quantiles=("0","0.005","0.025","0.25","0.5","0.75","0.975","0.995","1");
    my @spans=([$quantiles[$#quantiles],$quantiles[0]],
	       [$quantiles[$#quantiles-1],$quantiles[0+1]],
	       [$quantiles[$#quantiles-2],$quantiles[0+2]],
	       [$quantiles[$#quantiles-3],$quantiles[0+3]]);
    
    my $quant={};
    foreach my $i (0..$#quantiles) {
	my $q=$quantiles[$i];
	my $lvl=$q*$use_ndat;
	my @bracket_ix=(floor($lvl),ceil($lvl));
	if ($bracket_ix[1]>$use_ndat-1) {
	    $bracket_ix[0]--;	    $bracket_ix[1]--;
	}
	my $u=$lvl-$bracket_ix[0];
	$quant->{$q} = $zv[$bracket_ix[0]]*(1-$u) + $zv[$bracket_ix[1]]*($u);
    }
    my $spns={};
    foreach my $sp (@spans) {
	$spns->{$sp->[0]-$sp->[1]}=$quant->{$sp->[0]}-$quant->{$sp->[1]};
    }

#    ($zv[0],$zv[$#zv])=($zv[0]-0.05*($zv[$#zv]-$zv[0]),$zv[$#zv]+0.05*($zv[$#zv]-$zv[0]));

    {
	my ($llim,$ulim)=@{$quant}{@quantiles[2,6]};
	($zv[0],$zv[$#zv])=($llim-3*($ulim-$llim),$ulim+1*($ulim-$llim));
    }
    
    # adjust # bins if necessary for better plots
    $nbin=ceil(($zv[$#zv]-$zv[0])/$maxbinwid) if ($nbin<($zv[$#zv]-$zv[0])/$maxbinwid);

    # here construct the bin array
    my $hist={("bincen"   => [],
	       "data"     => [],
	       "nbin"     => $nbin,
	       "stepsize" => ($zv[$#zv]-$zv[0])/(1.0*$nbin),
	       "quant"    => $quant,
	       "qlvls"    => [sort {$a<=>$b} keys %{$quant}],
	       "span"     => $spns,
	       "splvls"   => [sort {$a<=>$b} keys %{$spns}])};

    for (my $i=0;$i<$hist->{"nbin"};$i++) {
	$hist->{"bincen"}->[$i] = $zv[0] + ($i+0.5) * $hist->{"stepsize"};
	$hist->{"data"}->[$i]=0;
    }
    # populate bins
    for (my $i=0;$i<$tnt->{"ndat"};$i++) {
	my $bin=floor(($tnt->{$axis}->[$i]-$zv[0])/$hist->{"stepsize"});
	next if ($bin*($hist->{"nbin"}-1-$bin)<0);
	$hist->{"data"}->[$bin]++;
    }
    # get maximum bin value
    my @dv=sort {$a<=>$b} @{$hist->{"data"}};
    # generate cumulative distribution and analyze
    $hist->{"cumdist"}=[];
    $hist->{"cumdist"}->[0]=0;
    for (my $i=1;$i<$hist->{"nbin"};$i++) {
	$hist->{"cumdist"}->[$i]=$hist->{"cumdist"}->[$i-1]+$hist->{"data"}->[$i-1];
    }
    my @cv=@{$hist->{"cumdist"}};
    for (my $i=1;$i<$hist->{"nbin"};$i++) {
	$hist->{"cumdist"}->[$i] *= ($dv[$#dv]/$cv[$#cv]);
    }
    ($dv[0],$dv[$#dv])=($dv[0]-0.05*($dv[$#dv]-$dv[0]),$dv[$#dv]+0.05*($dv[$#dv]-$dv[0]));
    $hist->{"zv"}=[@zv[0,$#zv]];
    $hist->{"dv"}=[@dv[0,$#dv]];
    $hist->{"labels"}={("x"=>$axis." [mm]",
			"y"=>"image height samples per bin",
			"title"=>$title)};
    return($hist);
}

sub draw_histogram {
    my ($hist)=@_;
    my @zv=@{$hist->{"zv"}};
    my @dv=@{$hist->{"dv"}};
    # plot
    pgscf(2);
    pgsch(1.2);
    pgenv(@zv[0,$#zv],@dv[0,$#dv],0,0);
    my %lbls=%{$hist->{"labels"}};
    pglabel(@lbls{"x","y","title"});
    pgbin($hist->{"nbin"},$hist->{"bincen"},$hist->{"data"},1);    # bin values are centered
    $hist->{"results"}=[];
    my @quantiles=@{$hist->{"qlvls"}};
    foreach my $i (0..$#quantiles) {
	my $q=$quantiles[$i];
	my $s=sprintf("%5.3f: %+5.3f",$q,$hist->{"quant"}->{$q});
	my ($xp,$yp)=($zv[0]+($zv[$#zv]-$zv[0])*0.1,$dv[$#dv]+($dv[0]-$dv[$#dv])*(0.1+$i*0.05));
	pgtext($xp,$yp,$s);
	# increment the results array
	push(@{$hist->{"results"}},sprintf("QUANTILE %6.4f\t%+9.2f micron",
					   $q,1000.0*$hist->{"quant"}->{$q}));
    }
    my @splvls=@{$hist->{"splvls"}};
    foreach my $i (0..$#splvls) {
	my $sp=$splvls[$i];
	my $s=sprintf("w%3d%%: %5.1f\\gmm",100*$sp,1000*$hist->{"span"}->{$sp});
	my ($xp,$yp)=($zv[0]+($zv[$#zv]-$zv[0])*0.1,$dv[$#dv]+($dv[0]-$dv[$#dv])*(0.6+$i*0.05));
	pgtext($xp,$yp,$s);
	# increment the results array
	push(@{$hist->{"results"}},sprintf("WIDTH %3d%%\t%6.2f micron",100*$sp,1000*$hist->{"span"}->{$sp}));
    }
    pgline($hist->{"nbin"},$hist->{"bincen"},$hist->{"cumdist"});
    pgiden();
}

sub pgimag_by_parts {
    my ($map)=@_;
    # do this segment by segment but don't plot values where there
    # are no samples.
    my $ntot=($map->{"dim"}->[0]*$map->{"dim"}->[1]);
    my $wrap=$map->{"dim"}->[0];
    my ($start,$stop)=(0,0);
    my ($x0,$y0,$x1,$y1);
    # first make a 1D array containing "samples"
    my $samples=[];
    for (my $yt=0;$yt<$map->{"dim"}->[1];$yt++) {
	push(@{$samples},
	     @{$map->{"samples"}->[$yt]}[0..$map->{"dim"}->[0]-1]);
    }
    # now pass through $samples to make up a list of ranges 
    # containing data..
    my $sr=[];
    my $dlims=[];
    while (($start<$ntot) && ($stop<$ntot)) {
	while (($start<$ntot) && ($samples->[$start]==0)) {
	    $start++;
	}
	$stop=$start;
	while (($stop<$ntot) && ($samples->[$stop]>0)) {
	    $stop++;
	}
	if (($stop-1 <= $ntot-1) && ($samples->[$stop-1]>0)) {
	    push(@{$sr},[$start,$stop-1]);
	}
	$start=$stop;
    }
    foreach my $r (@{$sr}) {
	($x0,$y0,$x1,$y1)=($r->[0] % $wrap,int($r->[0]/$wrap),
			   $r->[1] % $wrap,int($r->[1]/$wrap));
	if ($y1 == $y0) {
	    # draw a part of a single row
	    push(@{$dlims},({("x" => [$x0+1,$x1+1],
			      "y" => [$y0+1,$y1+1])}));
	} elsif ($y1 == $y0+1) {
	    # draw 2 rows
	    push(@{$dlims},({("x" => [$x0+1,$map->{"dim"}->[0]],
			      "y" => [$y0+1,$y0+1])},
			    {("x" => [1,$x1+1],
			      "y" => [$y1+1,$y1+1])}));
	} else {
	    # draw 1st row, a set of complet rows, and final row
	    push(@{$dlims},({("x" => [$x0+1,$map->{"dim"}->[0]],
			      "y" => [$y0+1,$y0+1])},
			    {("x" => [1,$map->{"dim"}->[0]],
			      "y" => [$y0+2,$y1])},
			    {("x" => [1,$x1+1],
			      "y" => [$y1+1,$y1+1])}));
	}
    }
    foreach my $dlim (@{$dlims}) {
	# printf "last (x1,y1)=(%d,%d)\n",$dlims->[$#{$dlims}]->{"x"}->[1],$dlims->[$#{$dlims}]->{"y"}->[1];

	#				printf "CHIP %d: (%d,%d) to (%d,%d)\n",$v*3+$h,$dlim->{"x"}->[0],$dlim->{"y"}->[0],$dlim->{"x"}->[1],$dlim->{"y"}->[1];
	
	pgimag($map->{"value"},
	       $map->{"dim"}->[0],$map->{"dim"}->[1],
	       @{$dlim->{"x"}},@{$dlim->{"y"}},
	       $map->{"zsc"}->[1],$map->{"zsc"}->[0],
	       $map->{"transform"});
    }
}

sub record_filename {
    my ($filenames)=@_;
    my $savesize;
    pgqch($savesize);
    my $os;
    if ($#{$filenames}-$[+1>=1) {
	pgsch(0.6);
	$os=0.5;
    } else {
	pgsch(0.7);
	$os=0.3;
    }

    foreach my $fn (reverse @{$filenames}) {
	pgmtxt("T",$os,0,0.0,$fn);
	$os++;
    }

    pgsch($savesize);
}

sub output_histogram_results {
    my ($output_root,$hist_results)=@_;
    open(G,">",$output_root."_results.txt") || die;
    foreach my $line (@{$hist_results}) {
	printf G "%s\n",$line;
    }
    close(G);
}
